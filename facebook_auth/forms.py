import copy
from datetime import datetime

from django import forms
from django.utils import timezone


class ParsedResponse(object):
    def __init__(self, parsed_data, is_valid, errors):
        self.parsed_data = parsed_data
        self.is_valid = is_valid
        self.errors = errors


class ListField(forms.MultiValueField):
    def clean(self, value):
        if hasattr(value, '__len__'):
            self.fields = [forms.CharField(required=False)
                           for _ in range(len(value))]
        return super(ListField, self).clean(value)

    def compress(self, data_list):
        return data_list


class TokenInformationForm(forms.Form):
    user_id = forms.CharField()
    token = forms.CharField()
    expires_at = forms.CharField()
    token_is_valid = forms.BooleanField()
    scopes = ListField(required=False)

    def __init__(self, initial, *args, **kwargs):
        super(TokenInformationForm, self).__init__(initial, *args, **kwargs)
        initial['token_is_valid'] = initial.get('is_valid', False)

    def clean_token_is_valid(self):
        if 'token_is_valid' not in self.cleaned_data:
            raise forms.ValidationError('No token status in response.')
        is_valid = self.cleaned_data['token_is_valid']
        if not is_valid:
            raise forms.ValidationError('Token is invalid.')
        return is_valid

    def clean_expires_at(self):
        timestamp = self.data['expires_at']
        naive = datetime.fromtimestamp(int(timestamp))
        return naive.replace(tzinfo=timezone.utc)


class FacebookResponseError(Exception):
    def __init__(self, errors):
        super(FacebookResponseError, self).__init__()
        self.errors = errors


def parse_facebook_response(raw_response, token):
    try:
        return try_to_parse_facebook_response(raw_response, token)
    except FacebookResponseError as e:
        return ParsedResponse(None, False, e.errors)


def try_to_parse_facebook_response(raw_response, token):
    if not isinstance(raw_response, dict):
        raise FacebookResponseError(['Facebook response should be dict.'])
    data = copy.deepcopy(raw_response.get('data', {}))
    if not isinstance(data, dict):
        raise FacebookResponseError(['Facebook data should be dict.'])
    data['token'] = token
    form = TokenInformationForm(data)
    if form.is_valid():
        return ParsedResponse(form.cleaned_data, True, None)
    else:
        raise FacebookResponseError(form.errors)
