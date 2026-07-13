from django.contrib import admin

from .models import FactDailyHealthSummary


@admin.register(FactDailyHealthSummary)
class FactDailyHealthSummaryAdmin(admin.ModelAdmin):
    list_display = ("districtname", "date", "anc_df_total_anc", "ci_patient_fully_immunized")
    list_filter = ("districtname", "date")
    search_fields = ("districtname",)
    date_hierarchy = "date"
