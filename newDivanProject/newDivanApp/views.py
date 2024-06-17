from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponse
from .models import *
from .models import Order, TechnicalSpecification, Contract
from django.core.serializers import serialize
from .forms import (NameForm, AvatarForm, PositionForm, StatusForm, CitizenshipForm, PassportForm, SalaryForm)
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Q
from decimal import Decimal
from datetime import datetime
from django.db.models import Sum
from django.contrib.auth import authenticate, login
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required


def logout_view(request):
    logout(request)
    return redirect('login')

def login_view(request):
    if request.user.is_authenticated:
        if request.user.is_staff:
            return redirect('main')  # Перенаправляем персонал на страницу администрирования
        else:
            return redirect('active')  # Обычные пользователи попадают на свой профиль

    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            if user.is_staff:
                return redirect('main')
            else:
                return redirect('active')
        else:
            return render(request, 'auth.html', {'error_message': 'Invalid login credentials'})

    return render(request, 'auth.html')

@login_required
def main_view(request):

    employee = Employee.objects.get(user=request.user)

    if employee.position.access_lvl < 2:
        return redirect('active')

    orders = Order.objects.all().select_related('contract').prefetch_related('technical_specifications')
    total_orders = orders.count()  # Подсчитываем количество заказов
    total_employees = Employee.objects.count()

    total_contract_value = Order.objects.aggregate(total_value_sum=Sum('contract__total_value'))['total_value_sum']
    if total_contract_value is None:
        total_contract_value = 0  # Handling cases where there are no orders/contracts


    completed_count = Order.objects.filter(status__in=['closed', 'delivered']).count()

    # Заказы в очереди
    queue_count = Order.objects.filter(status__in=[
        'to_do', 'registered', 'to_pickup', 'is_picked', 'to_deliver'
    ]).count()

    # Заказы в работе
    in_progress_count = Order.objects.filter(status__in=[
        'in_progress', 'in_review', 'suspended'
    ]).count()

    return render(request, 'main.html', {
        'orders': orders,
        'total_orders': total_orders,
        'total_employees': total_employees,
        'total_contract_value': total_contract_value,
        'completed_count': completed_count,
        'queue_count': queue_count,
        'in_progress_count': in_progress_count,
        'employee' : employee
    })

def calendar_view(request):
    return render(request, 'calendar.html')


def add_activity(request):
    worker_position = JobTitle.objects.filter(name='Рабочий').first()
    executors = Employee.objects.filter(position=worker_position) if worker_position else Employee.objects.none()
    orders = Order.objects.all()

    context = {
        'orders': orders,
        'executors': executors
    }
    return render(request, 'add_activity.html', context)
def active_view(request):
    departments = Department.objects.all()
    positions = JobTitle.objects.all()
    employees = Employee.objects.select_related('position', 'department').all()

    context = {
        'employees': employees,
        'departments': departments,
        'positions': positions
    }
    return render(request, 'active.html', context)








#ЗАКАЗЫ
def get_payment_status(contract, pickup_delivery):
    if not contract.is_prepayment_paid and not contract.is_postpayment_paid:
        return "Ожидает предоплаты"
    elif contract.is_prepayment_paid and not contract.is_postpayment_paid:
        if pickup_delivery and pickup_delivery.delivery_date:
            return "Ожидает оплаты"
        return "Внесена предоплата"
    elif contract.is_postpayment_paid:
        return "Оплата произведена"
    return "Неопределенный статус"

@login_required
def orders_view(request):
    employee = Employee.objects.get(user=request.user)

    if employee.position.access_lvl < 2:
        return redirect('active')


    orders = Order.objects.select_related(
        'contract', 'manager', 'executor1', 'executor2', 'executor3'
    ).prefetch_related('technical_specifications', 'pickupdelivery_set')

    total_count = orders.count()

    # Получаем параметры фильтрации из GET-запроса
    search_query = request.GET.get('search_query', '')
    status_filter = request.GET.get('status', '')
    type_filter = request.GET.get('type', '')
    payment_status_filter = request.GET.get('payment_status', '')
    start_date = request.GET.get('start_date', '')
    end_date = request.GET.get('end_date', '')

    # Фильтрация по номеру заказа или описанию
    if search_query:
        orders = orders.filter(
            Q(number__icontains=search_query) |
            Q(technical_specifications__short_descr__icontains=search_query)
        ).distinct()

    # Фильтрация по статусу заказа
    if status_filter:
        orders = orders.filter(status=status_filter)

    # Фильтрация по типу мебели
    if type_filter:
        orders = orders.filter(technical_specifications__furniture_type1=type_filter)

    # Расширенная фильтрация по статусу оплаты
    if payment_status_filter:
        if payment_status_filter == "awaiting_prepayment":
            orders = orders.filter(contract__is_prepayment_paid=False, contract__is_postpayment_paid=False)
        elif payment_status_filter == "prepayment_made":
            orders = orders.filter(contract__is_prepayment_paid=True, contract__is_postpayment_paid=False, pickupdelivery_set__delivery_date__isnull=True)
        elif payment_status_filter == "awaiting_payment":
            orders = orders.filter(contract__is_prepayment_paid=True, contract__is_postpayment_paid=False, pickupdelivery_set__delivery_date__isnull=False)
        elif payment_status_filter == "payment_done":
            orders = orders.filter(contract__is_postpayment_paid=True)

    if start_date and end_date:
        orders = orders.filter(contract__create_date__range=[start_date, end_date])

    # AJAX запрос для обновления таблицы заказов без перезагрузки страницы
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        data = format_orders_data(orders)
        return JsonResponse({'data': data, 'total_count': total_count}, safe=False)

    return render(request, 'orders.html', {
        'orders': orders
    })

def format_orders_data(orders):
    data = []
    for order in orders:
        pickup_delivery = order.pickupdelivery_set.first()
        payment_status = get_payment_status(order.contract, pickup_delivery)

        # Список исполнителей
        executors = []
        for executor in [order.executor1, order.executor2, order.executor3]:
            if executor:
                executors.append({
                    'avatar_url': executor.avatar.url if executor.avatar else '',
                    'full_name': f"{executor.first_name} {executor.last_name}"
                })

        # Добавление информации о менеджере
        manager = {
            'full_name': f"{order.manager.first_name} {order.manager.last_name}" if order.manager else "Нет данных",
            'avatar_url': order.manager.avatar.url if order.manager and order.manager.avatar else ''
        }

        data.append({
            'id': order.id,
            'number': order.number,
            'create_date': order.contract.create_date.strftime('%d.%m.%Y'),
            'completion_date': order.contract.completion_date.strftime('%d.%m.%Y'),
            'total_value': "{:,.2f}".format(order.contract.total_value).replace(",", " ").replace(".", ","),
            'type': order.technical_specifications.first().get_furniture_type1_display() if order.technical_specifications.exists() else '',
            'description': order.technical_specifications.first().short_descr if order.technical_specifications.exists() else '',
            'payment_status': payment_status,
            'status': order.get_status_display(),
            'executors': executors,
            'manager': manager  # Добавление информации о менеджере в вывод
        })
    return data


@csrf_exempt
@login_required
def add_order(request):
    employee = Employee.objects.get(user=request.user)

    if employee.position.access_lvl < 2:
        return redirect('active')

    manager_position = JobTitle.objects.filter(name='Менеджер').first()
    managers = Employee.objects.filter(position=manager_position) if manager_position else Employee.objects.none()
    worker_position = JobTitle.objects.filter(name='Рабочий').first()
    executors = Employee.objects.filter(position=worker_position) if worker_position else Employee.objects.none()

    if request.method == 'POST':
        #заказ
        number = request.POST.get('number')
        manager_id = request.POST.get('manager')
        executors_ids = request.POST.get('executors', '')
        executors_ids = executors_ids.split(',') if executors_ids else []
        source = request.POST.get('source')

        #договор
        contract_num = request.POST.get('contract_num')
        create_date = request.POST.get('create_date')
        completion_date = request.POST.get('completion_date')
        total_value = request.POST.get('total_value')
        payment_type = request.POST.get('payment_type')
        prepayment_share = request.POST.get('prepayment_share')
        prepayment_value = request.POST.get('prepayment_value')
        is_prepayment_paid = request.POST.get('is_prepayment_paid') == 'true'
        prepayment_date = request.POST.get('prepayment_date')
        postpayment_value = request.POST.get('postpayment_value')
        is_postpayment_paid = request.POST.get('is_postpayment_paid') == 'true'
        postpayment_date = request.POST.get('postpayment_date')

        #клиент
        address = request.POST.get('address')
        contact_number = request.POST.get('contact_number')
        full_name = request.POST.get('full_name')
        comments = request.POST.get('comments')


        #тех. задание
        items_qty = int(request.POST.get('items_qty'))
        short_descr = request.POST.get('short_descr')
        item_type = request.POST.get('item_type')
        furniture_type1 = request.POST.get('furniture_type1')
        work_types = request.POST.get('work_types').split(',')
        full_descr = request.POST.get('full_descr')
        photo1 = request.FILES.get('photo1', None)
        photo2 = request.FILES.get('photo2', None)
        photo3 = request.FILES.get('photo3', None)
        photo4 = request.FILES.get('photo4', None)
        technicalspecification_comments = request.POST.get('technicalspecification_comments')

        # Сбор данных о материалах из POST запроса
        material_name = request.POST.get('material_name')
        stock = request.POST.get('stock') == 'true'
        fitting_name = request.POST.get('fitting_name')
        fitting_in_stock = request.POST.get('fitting_in_stock') == 'true'
        material_comments = request.POST.get('material_comments')
        material_cost = float(request.POST.get('material_cost'))
        material_order_status = request.POST.get('material_order_status')
        material_order_date = request.POST.get('material_order_date')
        material_payment_status = request.POST.get('material_payment_status')
        material_payment_date = request.POST.get('material_payment_date')

        # Добавление данных забора
        is_picked = request.POST.get('pickupdelivery_is_picked') == 'true'
        pickup_date = request.POST.get('pickupdelivery_pickup_date')
        pickup_time = request.POST.get('pickupdelivery_pickup_time')
        pickup_type = request.POST.get('pickupdelivery_pickup_type')
        pickup_guy_id = request.POST.get('pickup_guy')
        pickup_comments = request.POST.get('pickupdelivery_pickup_comments')

        # Добавление данных доставки
        is_delivered = request.POST.get('pickupdelivery_is_delivered') == 'true'
        delivery_date = request.POST.get('pickupdelivery_delivery_date')
        delivery_time = request.POST.get('pickupdelivery_delivery_time')
        delivery_type = request.POST.get('pickupdelivery_delivery_type')
        delivery_guy_id = request.POST.get('delivery_guy')
        delivery_comments = request.POST.get('pickupdelivery_delivery_comments')


        # Create a Client instance
        client = Client(
            first_name=full_name.split()[1],
            last_name=full_name.split()[0] if len(full_name.split()) > 1 else '',
            middle_name=full_name.split()[2] if len(full_name.split()) > 2 else '',
            contact_number=contact_number,
            address=address,
            comments=comments
        )
        client.save()

        # Parse dates and calculate the duration
        create_date_dt = datetime.strptime(create_date, '%Y-%m-%d')
        completion_date_dt = datetime.strptime(completion_date, '%Y-%m-%d')
        duration = (completion_date_dt - create_date_dt).days


        # Create a Contract instance
        contract = Contract(
            num=contract_num,
            client=client,
            create_date=create_date_dt,
            completion_date=completion_date_dt,
            duration=duration,
            total_value=float(total_value),
            total_work_cost=float(total_value),
            payment_type=payment_type,
            prepayment_share=float(prepayment_share),
            prepayment_value=float(prepayment_value),
            is_prepayment_paid=is_prepayment_paid,
            prepayment_date=datetime.strptime(prepayment_date, '%Y-%m-%d') if prepayment_date else None,
            postpayment_value=float(postpayment_value),
            is_postpayment_paid=is_postpayment_paid,
            postpayment_date=datetime.strptime(postpayment_date, '%Y-%m-%d') if postpayment_date else None,
            comments=comments,
        )
        contract.save()

        # Create an Order instance
        manager = Employee.objects.get(id=manager_id)
        new_order = Order(
            number=number,
            manager=manager,
            source=source,
            contract=contract,
            status='registered',
            executor1 = Employee.objects.get(id=executors_ids[0]) if len(executors_ids) > 0 else None,
            executor2 = Employee.objects.get(id=executors_ids[1]) if len(executors_ids) > 1 else None,
            executor3 = Employee.objects.get(id=executors_ids[2]) if len(executors_ids) > 2 else None
        )
        new_order.save()

        # Создание технического задания
        TechnicalSpecification.objects.create(
            order=new_order,
            items_qty=items_qty,
            short_descr=short_descr,
            item_type=item_type,
            furniture_type1=furniture_type1,
            work_type1=work_types[0] if len(work_types) > 0 else None,
            work_type2=work_types[1] if len(work_types) > 1 else None,
            full_descr=full_descr,
            photo1=photo1,
            photo2=photo2,
            photo3=photo3,
            photo4=photo4,
            comments = technicalspecification_comments
        )

        # Создание объекта Material
        material = Material(
            order=new_order,
            name=material_name,
            in_stock=stock,
            cost=material_cost,
            order_status=material_order_status,
            order_date=datetime.strptime(material_order_date, '%Y-%m-%d') if material_order_date else None,
            payment_status=material_payment_status,
            payment_date=datetime.strptime(material_payment_date, '%Y-%m-%d') if material_payment_date else None,
            fitting_name=fitting_name,
            fitting_in_stock=fitting_in_stock,
            comments=material_comments
        )
        material.save()

        pickup = PickupDelivery(
            order=new_order,
            is_picked=is_picked,
            pickup_date=datetime.strptime(pickup_date, '%Y-%m-%d') if pickup_date else None,
            pickup_time=pickup_time,
            pickup_type=pickup_type,
            pickup_guy=Employee.objects.get(id=pickup_guy_id) if pickup_guy_id else None,
            pickup_comments=pickup_comments,
            is_delivered = is_delivered,
            delivery_date = datetime.strptime(delivery_date, '%Y-%m-%d') if delivery_date else None,
            delivery_time = delivery_time,
            delivery_type = delivery_type,
            delivery_guy = Employee.objects.get(id=delivery_guy_id) if delivery_guy_id else None,
            delivery_comments = delivery_comments
        )
        pickup.save()





        return redirect('orders')

    else:
        context = {
            'managers': managers,
            'executors': executors
        }
        return render(request, 'add_order.html', context)


@csrf_exempt
@login_required
def delete_order(request, order_id):

    employee = Employee.objects.get(user=request.user)

    if employee.position.access_lvl < 2:
        return redirect('active')

    if request.method == 'POST':
        try:
            order = Order.objects.get(pk=order_id)
            order.delete()
            return JsonResponse({'success': True})
        except Order.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Заказ не найден'})
    return JsonResponse({'success': False, 'error': 'Неверный запрос'})


@csrf_exempt
@login_required
def refactor_order(request, order_id):
    employee = Employee.objects.get(user=request.user)

    if employee.position.access_lvl < 2:
        return redirect('active')

    # Получаем заказ по ID
    order = get_object_or_404(Order, id=order_id)

    # Загружаем связанные данные
    contract = order.contract
    client = contract.client
    technical_specification = order.technical_specifications.first()
    materials = Material.objects.filter(order=order)
    pickups = PickupDelivery.objects.filter(order=order).first()


    # Загружаем список менеджеров и исполнителей
    manager_position = JobTitle.objects.filter(name='Менеджер').first()
    managers = Employee.objects.filter(position=manager_position) if manager_position else Employee.objects.none()
    worker_position = JobTitle.objects.filter(name='Рабочий').first()
    executors = Employee.objects.filter(position=worker_position) if worker_position else Employee.objects.none()

    if request.method == 'POST':
        # Обновляем клиента
        client.address = request.POST.get('address')
        client.contact_number = request.POST.get('contact_number')
        client.full_name = request.POST.get('full_name')
        client.comments = request.POST.get('comments')
        client.save()

        # Обновляем контракт
        contract.num = request.POST.get('contract_num')
        contract.create_date = datetime.strptime(request.POST.get('create_date'), '%Y-%m-%d')
        contract.completion_date = datetime.strptime(request.POST.get('completion_date'), '%Y-%m-%d')
        contract.total_value = float(request.POST.get('total_value'))
        contract.payment_type = request.POST.get('payment_type')
        contract.prepayment_share = float(request.POST.get('prepayment_share'))
        contract.prepayment_value = float(request.POST.get('prepayment_value'))
        contract.is_prepayment_paid = request.POST.get('is_prepayment_paid') == 'true'
        contract.prepayment_date = datetime.strptime(request.POST.get('prepayment_date'),
                                                     '%Y-%m-%d') if request.POST.get('prepayment_date') else None
        contract.postpayment_value = float(request.POST.get('postpayment_value'))
        contract.is_postpayment_paid = request.POST.get('is_postpayment_paid') == 'true'
        contract.postpayment_date = datetime.strptime(request.POST.get('postpayment_date'),
                                                      '%Y-%m-%d') if request.POST.get('postpayment_date') else None
        contract.comments = request.POST.get('comments')
        contract.save()

        # Обновляем заказ
        order.number = request.POST.get('number')
        order.manager_id = request.POST.get('manager')
        executors_ids = request.POST.get('executors', '').split(',') if request.POST.get('executors') else []
        order.executor1 = Employee.objects.get(id=executors_ids[0]) if len(executors_ids) > 0 else None
        order.executor2 = Employee.objects.get(id=executors_ids[1]) if len(executors_ids) > 1 else None
        order.executor3 = Employee.objects.get(id=executors_ids[2]) if len(executors_ids) > 2 else None
        order.source = request.POST.get('source')
        order.save()

        # Обновляем техническое задание
        technical_specification.items_qty = int(request.POST.get('items_qty'))
        technical_specification.short_descr = request.POST.get('short_descr')
        technical_specification.item_type = request.POST.get('item_type')
        technical_specification.furniture_type1 = request.POST.get('furniture_type1')
        work_types = request.POST.get('work_types').split(',')
        technical_specification.work_type1 = work_types[0] if len(work_types) > 0 else None
        technical_specification.work_type2 = work_types[1] if len(work_types) > 1 else None
        technical_specification.full_descr = request.POST.get('full_descr')
        technical_specification.photo1 = request.FILES.get('photo1', technical_specification.photo1)
        technical_specification.photo2 = request.FILES.get('photo2', technical_specification.photo2)
        technical_specification.photo3 = request.FILES.get('photo3', technical_specification.photo3)
        technical_specification.photo4 = request.FILES.get('photo4', technical_specification.photo4)
        technical_specification.comments = request.POST.get('technicalspecification_comments')
        technical_specification.save()

        # Обновляем материалы
        for material in materials:
            material.name = request.POST.get('material_name', material.name)
            material.in_stock = request.POST.get('stock') == 'true'
            material.fitting_name = request.POST.get('fitting_name', material.fitting_name)
            material.fitting_in_stock = request.POST.get('fitting_in_stock') == 'true'
            material.comments = request.POST.get('material_comments', material.comments)
            material.cost = float(request.POST.get('material_cost', material.cost))
            material.order_status = request.POST.get('material_order_status', material.order_status)
            material.order_date = datetime.strptime(request.POST.get('material_order_date'),
                                                    '%Y-%m-%d') if request.POST.get(
                'material_order_date') else material.order_date
            material.payment_status = request.POST.get('material_payment_status', material.payment_status)
            material.payment_date = datetime.strptime(request.POST.get('material_payment_date'),
                                                      '%Y-%m-%d') if request.POST.get(
                'material_payment_date') else material.payment_date
            material.save()

        # Обновляем информацию о заборе и доставке
        if pickups:
            pickups.is_picked = request.POST.get('pickupdelivery_is_picked') == 'true'
            pickups.pickup_date = datetime.strptime(request.POST.get('pickupdelivery_pickup_date'),
                                                    '%Y-%m-%d') if request.POST.get(
                'pickupdelivery_pickup_date') else pickups.pickup_date
            pickups.pickup_time = request.POST.get('pickupdelivery_pickup_time', pickups.pickup_time)
            pickups.pickup_type = request.POST.get('pickupdelivery_pickup_type', pickups.pickup_type)
            pickups.pickup_guy_id = Employee.objects.get(id=request.POST.get('pickup_guy')) if request.POST.get(
                'pickup_guy') else pickups.pickup_guy
            pickups.pickup_comments = request.POST.get('pickupdelivery_pickup_comments', pickups.pickup_comments)
            pickups.is_delivered = request.POST.get('pickupdelivery_is_delivered') == 'true'
            pickups.delivery_date = datetime.strptime(request.POST.get('pickupdelivery_delivery_date'),
                                                      '%Y-%m-%d') if request.POST.get(
                'pickupdelivery_delivery_date') else pickups.delivery_date
            pickups.delivery_time = request.POST.get('pickupdelivery_delivery_time', pickups.delivery_time)
            pickups.delivery_type = request.POST.get('pickupdelivery_delivery_type', pickups.delivery_type)
            pickups.delivery_guy_id = Employee.objects.get(id=request.POST.get('delivery_guy')) if request.POST.get(
                'delivery_guy') else pickups.delivery_guy
            pickups.delivery_comments = request.POST.get('pickupdelivery_delivery_comments', pickups.delivery_comments)
            pickups.save()

        return redirect('orders')

    else:
        executors_list = []
        if order.executor1:
            executors_list.append(order.executor1)
        if order.executor2:
            executors_list.append(order.executor2)
        if order.executor3:
            executors_list.append(order.executor3)


        context = {
            'order': order,
            'executors_list': executors_list,
            'contract': contract,
            'client': client,
            'technical_specification': technical_specification,
            'materials': materials,
            'pickup': pickups,
            'managers': managers,
            'executors': executors,
        }

        return render(request, 'refactor_order.html', context)


#СОТРУДНИКИ
@login_required
def staff_view(request):
    employee = Employee.objects.get(user=request.user)

    if employee.position.access_lvl < 2:
        return redirect('active')

    departments = Department.objects.all()
    positions = JobTitle.objects.all()
    employees = Employee.objects.select_related('position', 'department').all()
    total_count = employees.count()

    search_name = request.GET.get('search_name', '')
    if search_name:
        query = Q()
        for term in search_name.split():
            query |= Q(first_name__icontains=term) | Q(last_name__icontains=term) | Q(middle_name__icontains=term)
        employees = employees.filter(query)

    status = request.GET.get('status', '')
    if status:
        employees = employees.filter(status=status)

    department_id = request.GET.get('department', '')
    if department_id:
        employees = employees.filter(department_id=department_id)

    payment_type = request.GET.get('payment_type', '')
    if payment_type:
        employees = employees.filter(type_salary=payment_type)

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        data = [{
            'id': employee.id,
            'full_name': f"{employee.last_name} {employee.first_name} {employee.middle_name}",
            'position': employee.position.name if employee.position else "",
            'department': employee.department.name if employee.department else "",
            'status': employee.get_status_display(),
            'employment_date': employee.employment_date,
            'type_salary': employee.get_type_salary_display(),
            'salary': employee.salary
        } for employee in employees]

        return JsonResponse({'data': data, 'total_count': total_count}, safe=False)

    context = {
        'employees': employees,
        'departments': departments,
        'positions': positions
    }
    return render(request, 'staff.html', context)

@csrf_exempt
@login_required
def add_employee(request):
    employee = Employee.objects.get(user=request.user)

    if employee.position.access_lvl < 2:
        return redirect('active')

    departments = Department.objects.all()
    positions = JobTitle.objects.all()

    if request.method == 'POST':
        # Extract and handle form data
        full_name = request.POST.get('full_name', '').split()
        avatar = request.FILES.get('avatar', None)
        position_id = request.POST.get('position')
        department_id = request.POST.get('department')
        status = request.POST.get('status')
        employment_date = request.POST.get('employment_date')
        termination_date = request.POST.get('termination_date')
        citizenship = request.POST.get('citizenship')
        residence_address = request.POST.get('residence_address')
        passport_series = request.POST.get('passport_series')
        passport_number = request.POST.get('passport_number')
        passport_issued_by = request.POST.get('passport_issued_by')
        passport_issue_date = request.POST.get('passport_issue_date')
        type_salary = request.POST.get('type_salary')
        salary = request.POST.get('salary')
        payment_details = request.POST.get('payment_details')

        # Validate salary input
        try:
            salary = Decimal(salary) if salary.strip() else None
        except (ValueError, TypeError):
            return HttpResponse('Invalid salary input.', status=400)

        # Handle potential IndexError for names
        last_name = full_name[0] if len(full_name) > 0 else ''
        first_name = full_name[1] if len(full_name) > 1 else ''
        middle_name = full_name[2] if len(full_name) > 2 else ''

        # Create new Employee instance
        employee = Employee(
            first_name=first_name, last_name=last_name, middle_name=middle_name,
            avatar=avatar, position_id=position_id, department_id=department_id, status=status,
            employment_date=employment_date, termination_date=termination_date if termination_date else None,
            citizenship=citizenship, residence_address=residence_address,
            passport_series=passport_series, passport_number=passport_number,
            passport_issued_by=passport_issued_by, passport_issue_date=passport_issue_date,
            type_salary=type_salary, salary=salary, payment_details=payment_details
        )
        employee.save()

        return redirect('staff')  # Redirect to the staff list page
    else:
        # Pass positions and departments to the form
        context = {
            'departments': departments,
            'positions': positions
        }
        return render(request, 'add_employee.html', context)

@csrf_exempt
@login_required
def delete_employee(request, employee_id):
    employee = Employee.objects.get(user=request.user)

    if employee.position.access_lvl < 2:
        return redirect('active')

    if request.method == 'POST':
        try:
            employee = Employee.objects.get(pk=employee_id)
            employee.delete()
            return JsonResponse({'success': True})
        except Employee.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Сотрудник не найден'})
    return JsonResponse({'success': False, 'error': 'Неверный запрос'})

@csrf_exempt
@login_required
def refactor_employee(request, employee_id):
    employee = Employee.objects.get(user=request.user)

    if employee.position.access_lvl < 2:
        return redirect('active')

    employee = get_object_or_404(Employee, pk=employee_id)
    departments = Department.objects.all()
    positions = JobTitle.objects.all()

    if request.method == 'POST':
        # Парсинг данных из формы
        full_name = request.POST.get('full_name', '').split()
        avatar = request.FILES.get('avatar', employee.avatar)

        position_id = request.POST.get('position', employee.position)
        department_id = request.POST.get('department', employee.department)
        position = get_object_or_404(JobTitle, pk=position_id)  # Получаем объект должности
        department = get_object_or_404(Department, pk=department_id)  # Получаем объект отдела

        status = request.POST.get('status', employee.status)
        employment_date = request.POST.get('employment_date', employee.employment_date)
        termination_date = request.POST.get('termination_date', employee.termination_date)
        citizenship = request.POST.get('citizenship', employee.citizenship)
        residence_address = request.POST.get('residence_address', employee.residence_address)
        passport_series = request.POST.get('passport_series', employee.passport_series)
        passport_number = request.POST.get('passport_number', employee.passport_number)
        passport_issued_by = request.POST.get('passport_issued_by', employee.passport_issued_by)
        passport_issue_date = request.POST.get('passport_issue_date', employee.passport_issue_date)
        type_salary = request.POST.get('type_salary', employee.type_salary)

        salary = request.POST.get('salary', employee.salary)
        salary = None if salary == '' else salary

        # Преобразование зарплаты в Decimal, если она не None
        try:
            salary = Decimal(salary) if salary is not None else None
        except (ValueError, TypeError):
            return HttpResponse('Invalid salary input.', status=400)

        payment_details = request.POST.get('payment_details', employee.payment_details)

        # Обновление сотрудника
        employee.avatar = avatar
        employee.first_name = full_name[1] if len(full_name) > 1 else ''
        employee.last_name = full_name[0] if len(full_name) > 0 else ''
        employee.middle_name = full_name[2] if len(full_name) > 2 else ''
        employee.position = position
        employee.department = department
        employee.status = status
        employee.employment_date = employment_date
        employee.termination_date = termination_date if termination_date else None
        employee.citizenship = citizenship
        employee.residence_address = residence_address
        employee.passport_series = passport_series
        employee.passport_number = passport_number
        employee.passport_issued_by = passport_issued_by
        employee.passport_issue_date = passport_issue_date
        employee.type_salary = type_salary
        employee.salary = salary
        employee.payment_details = payment_details
        employee.save()

        return redirect('staff')  # Перенаправление на страницу со списком сотрудников
    else:
        context = {
            'employee': employee,
            'departments': departments,
            'positions': positions
        }
        return render(request, 'refactor_employee.html', context)