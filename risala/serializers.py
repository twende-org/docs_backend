from rest_framework import serializers
from .models import Risala

class RisalaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Risala
        fields = "__all__"
        read_only_fields = ["user"]

class AIStepRequestSerializer(serializers.Serializer):
    step = serializers.IntegerField(min_value=1)
    event_type = serializers.CharField(max_length=50, required=False)
    instruction = serializers.CharField(max_length=2000, required=False)
