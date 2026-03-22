from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import CustomUser, ArtistProfile


class RegisterForm(UserCreationForm):
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'input-field', 'placeholder': 'your@email.com'
        })
    )
    username = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'input-field', 'placeholder': 'Choose a username'
        })
    )
    user_type = forms.ChoiceField(
        choices=CustomUser.USER_TYPE_CHOICES,
        widget=forms.Select(attrs={'class': 'input-field'})
    )
    password1 = forms.CharField(
        label='Password',
        widget=forms.PasswordInput(attrs={
            'class': 'input-field', 'placeholder': 'Create a strong password'
        })
    )
    password2 = forms.CharField(
        label='Confirm Password',
        widget=forms.PasswordInput(attrs={
            'class': 'input-field', 'placeholder': 'Repeat your password'
        })
    )

    class Meta:
        model  = CustomUser
        fields = ('username', 'email', 'user_type', 'password1', 'password2')


class LoginForm(forms.Form):
    username = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'input-field', 'placeholder': 'Your username'
        })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'input-field', 'placeholder': 'Your password'
        })
    )


class ProfileEditForm(forms.ModelForm):
    """Edit basic user info — works for both listeners and artists."""
    class Meta:
        model  = CustomUser
        fields = ['username', 'email', 'bio', 'avatar']
        widgets = {
            'username': forms.TextInput(attrs={
                'class': 'input-field', 'placeholder': 'Username'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'input-field', 'placeholder': 'Email address'
            }),
            'bio': forms.Textarea(attrs={
                'class': 'input-field', 'rows': 4,
                'placeholder': 'Tell the world about yourself...'
            }),
            'avatar': forms.FileInput(attrs={
                'class': 'input-field', 'accept': 'image/*'
            }),
        }


class ArtistProfileEditForm(forms.ModelForm):
    """Extra fields for artist profiles."""
    class Meta:
        model  = ArtistProfile
        fields = ['stage_name', 'country', 'social_links']
        widgets = {
            'stage_name': forms.TextInput(attrs={
                'class': 'input-field', 'placeholder': 'Your artist name'
            }),
            'country': forms.TextInput(attrs={
                'class': 'input-field', 'placeholder': 'e.g. Cameroon'
            }),
            'social_links': forms.HiddenInput(),
        }
