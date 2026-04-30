# Generated manually for voucher backend discount fix

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0016_product_discount_percent_product_flash_sale'),
    ]

    operations = [
        migrations.AddField(
            model_name='voucher',
            name='discount_type',
            field=models.CharField(choices=[('amount', 'Giảm theo số tiền'), ('percent', 'Giảm theo phần trăm')], default='amount', max_length=20, verbose_name='Loại giảm giá'),
        ),
        migrations.AddField(
            model_name='voucher',
            name='discount_percent',
            field=models.IntegerField(default=0, verbose_name='Phần trăm giảm (%)'),
        ),
        migrations.AddField(
            model_name='order',
            name='voucher',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='app.voucher', verbose_name='Voucher đã dùng'),
        ),
        migrations.AddField(
            model_name='order',
            name='voucher_discount',
            field=models.FloatField(default=0, verbose_name='Số tiền được giảm'),
        ),
        migrations.AddField(
            model_name='order',
            name='final_total',
            field=models.FloatField(default=0, verbose_name='Tổng tiền sau giảm'),
        ),
    ]
