from django import forms

class CreateSessionForm(forms.Form):
    owner_name = forms.CharField(label="Owner name", max_length=100)
    width = forms.FloatField(label="Width (m)", min_value=0.1)
    height = forms.FloatField(label="Height (m)", min_value=0.1)


