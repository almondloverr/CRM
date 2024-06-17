from django.urls import path
from . import views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('main/', views.main_view, name='main'),
    path('calendar/', views.calendar_view, name='calendar'),
    path('active/', views.active_view, name='active'),
    path('add_activity/', views.add_activity, name='add_activity'),

    path('orders/', views.orders_view, name='orders'),
    path('add_order/', views.add_order, name='add_order'),
    path('delete-order/<int:order_id>/', views.delete_order, name='delete_order'),
    path('refactor_order/<int:order_id>/', views.refactor_order, name='refactor_order'),


    path('staff/', views.staff_view, name='staff'),
    path('add_employee/', views.add_employee, name='add_employee'),
    path('delete-employee/<int:employee_id>/', views.delete_employee, name='delete_employee'),
    path('refactor_employee/<int:employee_id>/', views.refactor_employee, name='refactor_employee'),

]

# Добавление маршрутов для обслуживания медиа-файлов в режиме разработки
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
