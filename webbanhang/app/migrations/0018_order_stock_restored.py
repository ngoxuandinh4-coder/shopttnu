# Generated manually for stock restore tracking
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0017_voucher_percent_order_discount'),
    ]

    operations = [
        migrations.AddField(
            model_name='order',
            name='stock_restored',
            field=models.BooleanField(default=False, verbose_name='Đã hoàn kho'),
        ),
    ]
