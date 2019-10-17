# Generated by Django 2.2.6 on 2019-10-16 15:28

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0007_auto_20191016_1520'),
    ]

    operations = [
        migrations.CreateModel(
            name='CategoryItemPhone',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('category', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='app.Category')),
                ('item', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='app.Item')),
                ('phone', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='app.Phone')),
            ],
        ),
    ]