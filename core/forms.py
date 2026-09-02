import json

from django import forms

from core.models import Dataset, QualityCheck

class QualityCheckForm(forms.ModelForm):


 class Meta:
    model = QualityCheck
    fields = [
        "name",
        "check_type",
        "column_name",
        "configuration",
        "is_active",
    ]

    widgets = {
        "name": forms.TextInput(
            attrs={
                "placeholder": "e.g. Email must be valid",
                "class": "form-input",
            }
        ),
        "check_type": forms.Select(
            attrs={
                "class": "form-input",
            }
        ),
        "column_name": forms.TextInput(
            attrs={
                "placeholder": "e.g. email",
                "class": "form-input",
            }
        ),
        "configuration": forms.Textarea(
            attrs={
                "placeholder": '{"minimum": 18, "maximum": 100}',
                "class": "form-input",
                "rows": 4,
            }
        ),
        "is_active": forms.CheckboxInput(
            attrs={
                "class": "form-checkbox",
            }
        ),
    }

def __init__(self, *args, dataset=None, **kwargs):
    super().__init__(*args, **kwargs)

    self.dataset = dataset

    if dataset is not None:
        columns = []

        schema = dataset.schema_snapshot or {}

        for column in schema.get("columns", []):
            if isinstance(column, dict):
                name = column.get("name")

                if name:
                    columns.append(name)

        if not columns:
            for column in schema.get("schema", []):
                if isinstance(column, dict):
                    name = column.get("name")

                    if name:
                        columns.append(name)

        self.fields["column_name"] = forms.ChoiceField(
            required=False,
            choices=[
                ("", "Dataset-level check"),
                *[
                    (column, column)
                    for column in columns
                ],
            ],
            widget=forms.Select(
                attrs={
                    "class": "form-input",
                }
            ),
        )

def clean_name(self):
    name = self.cleaned_data["name"].strip()

    if not name:
        raise forms.ValidationError(
            "Quality check name cannot be empty."
        )

    return name

def clean_column_name(self):
    column_name = self.cleaned_data.get("column_name")

    if column_name:
        column_name = column_name.strip()

    return column_name

def clean_configuration(self):
    configuration = self.cleaned_data.get(
        "configuration"
    )

    if not configuration:
        return {}

    if isinstance(configuration, dict):
        return configuration

    try:
        configuration = json.loads(configuration)
    except (TypeError, ValueError):
        raise forms.ValidationError(
            "Configuration must contain valid JSON."
        )

    if not isinstance(configuration, dict):
        raise forms.ValidationError(
            "Configuration must be a JSON object."
        )

    return configuration

def clean(self):
    cleaned_data = super().clean()

    check_type = cleaned_data.get("check_type")
    column_name = cleaned_data.get("column_name")
    configuration = cleaned_data.get(
        "configuration",
        {}
    )

    dataset_level_checks = {
        "DUPLICATE",
        "SCHEMA",
        "FRESHNESS",
    }

    if (
        check_type
        and check_type not in dataset_level_checks
        and not column_name
    ):
        self.add_error(
            "column_name",
            "This quality check requires a column.",
        )

    if check_type == "RANGE":
        minimum = configuration.get("minimum")
        maximum = configuration.get("maximum")

        if minimum is None and maximum is None:
            self.add_error(
                "configuration",
                "Range checks require at least a minimum or maximum value.",
            )

        if (
            minimum is not None
            and maximum is not None
        ):
            try:
                if float(minimum) > float(maximum):
                    self.add_error(
                        "configuration",
                        "Minimum cannot be greater than maximum.",
                    )
            except (TypeError, ValueError):
                self.add_error(
                    "configuration",
                    "Minimum and maximum must be numeric.",
                )

    return cleaned_data

