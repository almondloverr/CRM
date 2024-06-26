# Generated by Django 4.2.11 on 2024-05-10 20:11

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('newDivanApp', '0002_alter_employee_type_salary_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='Event',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=200)),
                ('start', models.DateTimeField()),
                ('end', models.DateTimeField()),
                ('all_day', models.BooleanField(default=False)),
            ],
        ),
    ]
