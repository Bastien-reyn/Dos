# Generated by Django 2.2.6 on 2020-01-27 16:01

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0022_remove_categoryitemphonerepair_phone'),
    ]

    operations = [
        migrations.AlterField(
            model_name='item',
            name='sell_promo',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.DO_NOTHING, to='app.Promo'),
        ),
    ]
