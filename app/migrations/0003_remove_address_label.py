# Generated by Django 2.2.6 on 2019-12-17 10:14

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0002_auto_20191217_1013'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='address',
            name='label',
        ),
    ]
