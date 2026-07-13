"""
Unmanaged model mapped to Supabase PostgreSQL health summary table.
Data is read-only from the warehouse; ETL loads rows externally.
"""
from django.conf import settings
from django.db import models


class FactDailyHealthSummary(models.Model):
    """Daily district-level health program indicators."""

    districtname = models.CharField(max_length=100, blank=True, null=True, db_index=True)
    date = models.DateField(db_index=True)

    anc_df_total_records = models.IntegerField(null=True, blank=True)
    anc_df_unique_mothers = models.IntegerField(null=True, blank=True)
    anc_df_total_anc = models.IntegerField(null=True, blank=True)
    anc_df_diabetes_count = models.IntegerField(null=True, blank=True)
    anc_df_trimester_1st_trimester = models.IntegerField(null=True, blank=True)
    anc_df_trimester_2nd_trimester = models.IntegerField(null=True, blank=True)
    anc_df_trimester_3rd_trimester = models.IntegerField(null=True, blank=True)
    anc_df_bmi_normal = models.IntegerField(null=True, blank=True)
    anc_df_bmi_obese = models.IntegerField(null=True, blank=True)
    anc_df_bmi_overweight = models.IntegerField(null=True, blank=True)
    anc_df_bmi_underweight = models.IntegerField(null=True, blank=True)
    anc_df_bmi_nan = models.IntegerField(null=True, blank=True)
    anc_df_htn_elevated_unknown = models.IntegerField(null=True, blank=True)
    anc_df_htn_hypertension = models.IntegerField(null=True, blank=True)
    anc_df_htn_normal = models.IntegerField(null=True, blank=True)
    anc_df_htn_severe_hypertension = models.IntegerField(null=True, blank=True)

    mi_patient_total_records = models.IntegerField(null=True, blank=True)
    mi_patient_has_mi = models.IntegerField(null=True, blank=True)
    mi_patient_minimum_protected = models.IntegerField(null=True, blank=True)
    mi_patient_fully_immunized_mother = models.IntegerField(null=True, blank=True)

    child_patient_total_records = models.IntegerField(null=True, blank=True)
    child_patient_has_cn = models.IntegerField(null=True, blank=True)
    child_patient_children_under_5 = models.IntegerField(null=True, blank=True)
    child_patient_sam = models.IntegerField(null=True, blank=True)
    child_patient_mam = models.IntegerField(null=True, blank=True)

    ci_patient_total_records = models.IntegerField(null=True, blank=True)
    ci_patient_has_ci = models.IntegerField(null=True, blank=True)
    ci_patient_fully_immunized = models.IntegerField(null=True, blank=True)
    ci_patient_due = models.IntegerField(null=True, blank=True)
    ci_patient_defaulter = models.IntegerField(null=True, blank=True)

    pnc_patient_total_records = models.IntegerField(null=True, blank=True)
    pnc_patient_has_pnc = models.IntegerField(null=True, blank=True)
    pnc_patient_early_breastfeeding_initiation = models.IntegerField(null=True, blank=True)
    pnc_patient_breastfeeding_counseling = models.IntegerField(null=True, blank=True)
    pnc_patient_hypertension = models.IntegerField(null=True, blank=True)

    fp_patient_total_records = models.IntegerField(null=True, blank=True)
    fp_patient_has_fp_counsel = models.IntegerField(null=True, blank=True)
    fp_patient_commodity_received = models.IntegerField(null=True, blank=True)
    fp_patient_method_condom = models.IntegerField(null=True, blank=True)
    fp_patient_method_iud = models.IntegerField(null=True, blank=True)
    fp_patient_method_implant = models.IntegerField(null=True, blank=True)
    fp_patient_method_injectable = models.IntegerField(null=True, blank=True)
    fp_patient_method_none = models.IntegerField(null=True, blank=True)
    fp_patient_method_oral_pills = models.IntegerField(null=True, blank=True)
    fp_patient_method_other_unknown = models.IntegerField(null=True, blank=True)

    created_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        managed = False
        db_table = getattr(settings, "HEALTH_DB_TABLE", "fact_daily_health_summary")
        ordering = ["-date", "districtname"]

    def __str__(self) -> str:
        return f"{self.districtname} ({self.date})"
