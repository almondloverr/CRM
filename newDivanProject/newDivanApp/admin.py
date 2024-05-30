from django.contrib import admin
from .models import *

@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ['position', 'department', 'status', 'employment_date', 'avatar', 'first_name', 'last_name']
    list_filter = ['department', 'status']
    search_fields = ['first_name', 'last_name', 'residence_address', 'passport_number']

@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ['name', 'descr']

@admin.register(JobTitle)
class JobTitleAdmin(admin.ModelAdmin):
    list_display = ['name', 'descr']

@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ['first_name', 'last_name', 'middle_name', 'contact_number', 'address', 'comments']
    list_filter = ['address']
    search_fields = ['first_name', 'last_name', 'contact_number', 'address']

@admin.register(Firm)
class FirmAdmin(admin.ModelAdmin):
    list_display = ['short_name', 'full_name', 'contact', 'INN', 'KPP', 'OGRN', 'legal_address', 'actual_address',
                    'contact_number', 'corporate_number', 'comments']
    list_filter = ['legal_address', 'actual_address', 'INN']
    search_fields = ['short_name', 'full_name', 'INN', 'OGRN']

@admin.register(Contract)
class ContractAdmin(admin.ModelAdmin):
    list_display = ['num', 'client', 'firm', 'create_date', 'completion_date', 'duration', 'total_value', 
                    'total_work_cost', 'payment_type', 'prepayment_share', 'prepayment_value', 'prepayment_date', 
                    'is_prepayment_paid', 'postpayment_value', 'postpayment_date', 'is_postpayment_paid', 'comments']
    list_filter = ['create_date', 'completion_date', 'is_prepayment_paid', 'is_postpayment_paid']
    search_fields = ['client__last_name', 'firm__short_name', 'total_value']

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['number', 'contract', 'manager', 'source', 'status', 'executor1', 'executor2', 'executor3', 'comments']
    list_filter = ['status', 'source', 'manager', 'executor1', 'executor2', 'executor3']
    search_fields = ['number', 'manager__first_name', 'manager__last_name']

@admin.register(TechnicalSpecification)
class TechnicalSpecificationAdmin(admin.ModelAdmin):
    list_display = ['order', 'items_qty', 'short_descr', 'work_type1', 'work_type2', 'furniture_type1',
                    'furniture_type2', 'item_type', 'comments', 'photo1', 'photo2', 'photo3', 'photo4']
    list_filter = ['work_type1', 'work_type2', 'furniture_type1', 'furniture_type2']
    search_fields = ['short_descr', 'full_descr', 'item_type']

@admin.register(Activity)
class ActivityAdmin(admin.ModelAdmin):
    list_display = ['order', 'employee', 'status', 'activity_descr', 'date_start', 'date_review', 'date_end',
                    'total_work_cost', 'is_paid', 'payment_date', 'photo1', 'photo2', 'photo3', 'photo4']
    list_filter = ['status', 'date_start', 'date_end', 'is_paid']
    search_fields = ['order__number', 'employee__last_name']

@admin.register(Material)
class MaterialAdmin(admin.ModelAdmin):
    list_display = ['order', 'name', 'in_stock', 'order_status', 'cost', 'order_date', 'payment_status', 'payment_date',
                    'fitting_name', 'fitting_in_stock', 'comments']
    list_filter = ['in_stock', 'order_status', 'payment_status']
    search_fields = ['name', 'order__number']

@admin.register(PickupDelivery)
class PickupDeliveryAdmin(admin.ModelAdmin):
    list_display = ['order', 'is_picked', 'pickup_date', 'pickup_time', 'pickup_type', 'pickup_guy', 'is_delivered',
                    'delivery_date', 'delivery_time', 'delivery_type', 'delivery_guy', 'pickup_comments', 'delivery_comments']
    list_filter = ['is_picked', 'is_delivered', 'pickup_type', 'delivery_type']
    search_fields = ['order__number', 'pickup_type', 'delivery_type']
