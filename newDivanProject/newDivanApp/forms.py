
from django import forms
from .models import Employee

class NameForm(forms.ModelForm):
    full_name = forms.CharField(label="ФИО")

    class Meta:
        model = Employee
        fields = []

    def save(self, commit=True):
        full_name = self.cleaned_data.get('full_name').split()
        self.instance.last_name = full_name[0]
        self.instance.first_name = full_name[1]
        self.instance.middle_name = full_name[2] if len(full_name) > 2 else ''
        return super().save(commit)

class AvatarForm(forms.ModelForm):
    class Meta:
        model = Employee
        fields = ['avatar']

class PositionForm(forms.ModelForm):
    class Meta:
        model = Employee
        fields = ['position', 'department']

class StatusForm(forms.ModelForm):
    class Meta:
        model = Employee
        fields = ['status', 'employment_date', 'termination_date']
        widgets = {
            'employment_date': forms.DateInput(attrs={'type': 'date'}),
            'termination_date': forms.DateInput(attrs={'type': 'date'})
        }

class CitizenshipForm(forms.ModelForm):
    class Meta:
        model = Employee
        fields = ['citizenship', 'residence_address']

class PassportForm(forms.ModelForm):
    class Meta:
        model = Employee
        fields = ['passport_series', 'passport_number', 'passport_issued_by', 'passport_issue_date']
        widgets = {
            'passport_issue_date': forms.DateInput(attrs={'type': 'date'}),
        }

class SalaryForm(forms.ModelForm):
    class Meta:
        model = Employee
        fields = ['type_salary', 'salary', 'payment_details']
