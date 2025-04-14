from django import forms

class ChatViewForm(forms.Form):
   multimodal = forms.BooleanField(required=False, label="Использовать мультимодальную модель")
   image = forms.ImageField(required=False, label="Загрузить изображение")
   prompt = forms.CharField(widget=forms.Textarea, label="Текст запроса")
   temperature = forms.FloatField(initial=0.7)