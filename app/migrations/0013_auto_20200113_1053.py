# Generated by Django 2.2.6 on 2020-01-13 10:53

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0012_promo_tag'),
    ]

    operations = [
        migrations.AddField(
            model_name='item',
            name='sell_price',
            field=models.FloatField(default=0.0),
        ),
        migrations.AddField(
            model_name='item',
            name='sell_promo',
            field=models.ForeignKey(default=1, on_delete=django.db.models.deletion.DO_NOTHING, to='app.Promo'),
            preserve_default=False,
        ),
    ]
