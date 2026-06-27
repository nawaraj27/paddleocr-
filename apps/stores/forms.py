from django import forms

from .models import Store


class StoreForm(forms.ModelForm):
    class Meta:
        model = Store
        fields = ("name", "currency", "address", "phone", "logo",
                  "allow_negative_stock")
