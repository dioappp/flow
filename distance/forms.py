from django import forms


class DateInput(forms.DateInput):
    input_type = "date"


class UploadFileForm(forms.Form):
    date = forms.DateTimeField(
        widget=DateInput,
        help_text="Pilih tanggal yang ingin diekstrak dari File Distance",
    )
    file_OB = forms.FileField(label="File OB", allow_empty_file=False, required=True)
    file_Coal = forms.FileField(
        label="File Coal", allow_empty_file=False, required=True
    )
