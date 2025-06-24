from django import forms

class ChatViewForm(forms.Form):
   multimodal = forms.BooleanField(required=False, label="Use multimodal")
   image = forms.ImageField(required=False, label="Load image")
   prompt = forms.CharField(widget=forms.Textarea, label="Text request")
   temperature = forms.FloatField(initial=0.7)
