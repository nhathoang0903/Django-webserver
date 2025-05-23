# Generated manually for product logging models

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('cartv2', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='ProductEditLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('product_id', models.IntegerField()),
                ('product_name', models.CharField(max_length=255)),
                ('field_changed', models.CharField(max_length=100)),
                ('old_value', models.TextField(blank=True, null=True)),
                ('new_value', models.TextField(blank=True, null=True)),
                ('edited_by', models.CharField(default='admin', max_length=100)),
                ('timestamp', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'db_table': 'product_edit_logs',
                'ordering': ['-timestamp'],
            },
        ),
        migrations.CreateModel(
            name='ProductDeletionLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('product_id', models.IntegerField()),
                ('product_name', models.CharField(max_length=255)),
                ('product_data', models.JSONField()),
                ('deleted_by', models.CharField(default='admin', max_length=100)),
                ('timestamp', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'db_table': 'product_deletion_logs',
                'ordering': ['-timestamp'],
            },
        ),
    ] 