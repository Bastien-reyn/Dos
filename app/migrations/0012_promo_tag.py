# Generated by Django 2.2.6 on 2020-01-13 10:42

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0011_promo'),
    ]

    operations = [
        migrations.AddField(
            model_name='promo',
            name='tag',
            field=models.CharField(default='', max_length=20),
            preserve_default=False,
        ),
    ]