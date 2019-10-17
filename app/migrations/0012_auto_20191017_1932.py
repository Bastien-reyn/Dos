# Generated by Django 2.2.6 on 2019-10-17 19:32

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0011_auto_20191017_1925'),
    ]

    operations = [
        migrations.AlterField(
            model_name='categoryitemphonerepair',
            name='category',
            field=models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to='app.Category'),
        ),
        migrations.AlterField(
            model_name='categoryitemphonerepair',
            name='item',
            field=models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to='app.Item'),
        ),
        migrations.AlterField(
            model_name='categoryitemphonerepair',
            name='phone',
            field=models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to='app.Phone'),
        ),
        migrations.AlterField(
            model_name='categoryitemphonerepair',
            name='repair',
            field=models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='app.Repair'),
        ),
    ]
