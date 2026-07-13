from rest_framework import serializers


class ProtectionConfigSerializer(serializers.Serializer):
    fields = serializers.ListField(
        child=serializers.CharField(max_length=200), required=True
    )
    tags = serializers.ListField(
        child=serializers.CharField(max_length=200), required=True
    )

    def validate_fields(self, value):
        fields = [field.strip() for field in value]
        expected = self.context["deck"].note_type.field_names
        unknown = [field for field in fields if field not in expected]
        if unknown:
            raise serializers.ValidationError(
                f"Campos desconhecidos: {', '.join(unknown)}."
            )
        return list(dict.fromkeys(fields))

    def validate_tags(self, value):
        tags = [tag.strip() for tag in value]
        if any(not tag for tag in tags):
            raise serializers.ValidationError("Tags não podem ser vazias.")
        return list(dict.fromkeys(tags))
