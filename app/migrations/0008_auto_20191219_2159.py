# Generated by Django 2.2.6 on 2019-12-19 21:59

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0007_category_is_on_invoice'),
    ]

    operations = [
        migrations.AlterField(
            model_name='category',
            name='others',
            field=models.ManyToManyField(blank=True, null=True, related_name='_category_others_+', to='app.Category'),
        ),
    ]
