from rest_framework import serializers

from api import models


class EnvironmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Environment
