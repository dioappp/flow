from django import forms


class UploadFileForm(forms.Form):
    file = forms.FileField(label="Upload File", allow_empty_file=False)
