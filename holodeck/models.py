import uuid
import urllib
import json

from django.contrib.auth.models import User
from django.db import models
from holodeck.utils import get_widget_type_choices, load_class_by_string
from datetime import datetime


class Dashboard(models.Model):
    name = models.CharField(max_length=255)
    owner = models.ForeignKey(User, null=True)

    def __unicode__(self):
        return self.name


class Metric(models.Model):
    name = models.CharField(max_length=255)
    dashboard = models.ForeignKey('holodeck.Dashboard')
    widget_type = models.CharField(
        max_length=64,
        choices=get_widget_type_choices()
    )
    api_key = models.CharField(
        max_length=32,
        unique=True,
        blank=True,
        null=True
    )
    url = models.URLField(
        blank=True,
        null=True
    )

    def __unicode__(self):
        return self.name

    @classmethod
    def generate_api_key(cls):
        return uuid.uuid4().hex

    def render(self):
        return load_class_by_string(self.widget_type)().render(self)

    def save(self, *args, **kwargs):
        if not self.api_key:
            self.api_key = Metric.generate_api_key()
        super(Metric, self).save(*args, **kwargs)

    def _load_url_data(self):
        if getattr(self, 'data_cache', None):
            return self.data_cache
        data = json.loads(urllib.urlopen(self.url).read())
        data = [
            Sample(
                string_value = d['target'],
                integer_value = float(s[0]),
                timestamp = datetime.fromtimestamp(s[1]),
                metric = self,
            ) for d in data for s in d['datapoints']
        ]
        self.data_cache = sorted(data, key=lambda s: s.timestamp)
        return self.data_cache

    def get_samples(self, group, sample_count):
        if not self.url:
            return self.sample_set.filter(
                string_value=group
            ).order_by('-timestamp')[:sample_count]
        data = self._load_url_data()
        return [s for s in data if s.string_value == group][::-1][:sample_count]


class Sample(models.Model):
    metric = models.ForeignKey('holodeck.Metric')
    integer_value = models.IntegerField()
    string_value = models.CharField(max_length=64)
    timestamp = models.DateTimeField()
