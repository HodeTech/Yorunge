from typing import Literal

ErrorCode = Literal[
    "approval_required",
    "input_unsupported",
    "input_invalid",
    "input_changed",
    "input_budget_exceeded",
    "execution_timeout",
    "plan_not_found",
    "plan_not_valid",
    "plan_capacity_exceeded",
    "invalid_request",
    "invalid_config",
    "invalid_recipe",
    "invalid_plan",
    "file_unreadable",
    "profile_not_found",
    "unsupported_combination",
    "tool_unavailable",
    "credential_unavailable",
    "invalid_credential",
    "invalid_service_target",
    "state_invalid",
    "state_busy",
    "state_repair_required",
    "state_write_failed",
    "state_unsupported",
    "state_changed",
    "credential_revision_exhausted",
    "state_restore_unsupported",
    "config_exists",
    "config_conflict",
    "config_busy",
    "config_write_failed",
    "config_write_uncertain",
    "config_unsupported",
    "capability_expired",
    "capability_capacity_exceeded",
]

MESSAGES: dict[ErrorCode, str] = {
    "approval_required": "Açık onay gerekli. Güncel plan digest'ini confirm ile verin.",
    "input_unsupported": "Güvenli dosya bağlama bu platformda desteklenmiyor.",
    "input_invalid": "Girdi kökü veya dosya geçersiz. Açık kök ve düzenli göreli dosya kullanın.",
    "input_changed": "Girdi veya kök kimliği değişti. Güncel içerikle yeni plan hazırlayın.",
    "input_budget_exceeded": "Yerel girdi okuma sınırı 1 GiB. Daha dar bir girdi hazırlayın.",
    "execution_timeout": "Execution hazırlığı veya doğrulaması 30 saniyelik bütçeyi aştı.",
    "plan_not_found": "Kayıtlı plan bulunamadı. Plan listesini inceleyin.",
    "plan_not_valid": (
        "Execution planı güncel ve onaylanabilir değil. Engelleri ve bağları inceleyin."
    ),
    "plan_capacity_exceeded": (
        "Plan kotası dolu. Listeyi inceleyip seçili eski planı açıkça unutun."
    ),
    "capability_expired": (
        "Yetenek kanıtının süresi veya saat/bekleme bütçesi geçersiz. Güncel kaydı inceleyin."
    ),
    "capability_capacity_exceeded": (
        "Yetenek önbelleği kotası dolu; taze çelişkili kanıtlar korunuyor. Süreleri inceleyin."
    ),
    "invalid_request": "İstek geçersiz. Komut yardımındaki alanları ve türleri kontrol edin.",
    "invalid_config": "Profil geçersiz. v1 alanlarını, türleri ve anahtarları kontrol edin.",
    "invalid_recipe": "Reçete geçersiz. v1 alanlarını, türleri ve YAML sınırlarını kontrol edin.",
    "invalid_plan": "Plan geçersiz. Şema, seçimler veya digest eşleşmiyor; yeniden hazırlayın.",
    "file_unreadable": "Yerel dosya okunamadı. Dosyanın varlığını ve erişim iznini kontrol edin.",
    "profile_not_found": "Seçilen profil bulunamadı. Config içindeki profil adını kontrol edin.",
    "unsupported_combination": "Görev, araç, ortam veya parametre birleşimi desteklenmiyor.",
    "tool_unavailable": "Seçilen araç tanınmıyor. Açıkça kayıtlı bir araç kimliği seçin.",
    "credential_unavailable": (
        "Seçilen hizmetin sır referansı veya değeri eksik. Profil ve env ayarını kontrol edin."
    ),
    "invalid_credential": (
        "Seçilen hizmetin sır değeri geçersiz. UTF-8 ve uzunluk sınırını kontrol edin."
    ),
    "invalid_service_target": (
        "Hizmet hedefi credential kullanımı için geçersiz. HTTPS adresini kontrol edin."
    ),
    "state_invalid": "Yerel durum geçersiz. Sahiplik, izin ve bütünlük denetimini çalıştırın.",
    "state_busy": "Yerel durum meşgul veya süre bütçesi doldu. Etkin işlemi kontrol edin.",
    "state_repair_required": "Yerel durum onarım gerektiriyor. Açık kurtarma akışını kullanın.",
    "state_write_failed": (
        "Yerel durum kalıcılaştırılamadı. Disk ve tanılama sonucunu kontrol edin."
    ),
    "state_unsupported": "Yerel durum için desteklenen macOS/Linux ve SQLite 3.37+ gereklidir.",
    "state_changed": "Yerel bağ değişti. Güncel durumu inceleyip isteği yeniden hazırlayın.",
    "credential_revision_exhausted": (
        "Credential nesil sınırına ulaşıldı. Açık kimlik reset akışını kullanın."
    ),
    "state_restore_unsupported": (
        "Bu runtime veya snapshot türü için DB restore desteklenmiyor. Kimlik reset'i ayrıdır."
    ),
    "config_exists": "Config zaten var. İlk oluşturma mevcut dosyanın üzerine yazmaz.",
    "config_unsupported": (
        "Config yazımı için desteklenen macOS/Linux yerel dosya ortamı gereklidir."
    ),
    "config_busy": "Config başka bir yazım tarafından kilitli. Etkin işlemi kontrol edin.",
    "config_conflict": (
        "Config başka bir yazımla değişti. Güncel dosyayı inceleyip yeniden hazırlayın."
    ),
    "config_write_failed": "Config yazılamadı. Dosya izinlerini ve diski kontrol edin.",
    "config_write_uncertain": (
        "Config yayınlandı veya yayın durumu belirsiz. "
        "Dosyayı ve backup'ı inceleyin; otomatik tekrar yok."
    ),
}


class YorungeError(Exception):
    """Safe public failure: never attaches parser input, paths or provider bodies."""

    def __init__(self, code: ErrorCode) -> None:
        self.code = code
        self.message = MESSAGES[code]
        self.exit_code = 2
        if code == "approval_required":
            self.exit_code = 4
        elif code == "config_write_uncertain":
            self.exit_code = 5
        elif code in ("credential_unavailable", "invalid_credential"):
            self.exit_code = 3
        super().__init__(self.message)

    def envelope(self) -> dict[str, object]:
        return {
            "schema_version": 1,
            "code": self.code,
            "message": self.message,
            "operation_id": None,
            "retryable": False,
            "details": {},
        }


class ApprovalNotEffective(YorungeError):
    """A committed local record is visible even when terminal validity has elapsed."""

    def __init__(self, plan_id: str, approval_id: str) -> None:
        super().__init__("plan_not_valid")
        self.plan_id, self.approval_id = plan_id, approval_id
        self.message = (
            "Onay kaydı oluştu fakat son kontrolde etkin değil. "
            "plan execution show ile kayıtlı planı inceleyin."
        )
        self.args = (self.message,)

    def envelope(self) -> dict[str, object]:
        value = super().envelope()
        value["details"] = {
            "plan_id": self.plan_id,
            "approval_id": self.approval_id,
            "recorded": True,
        }
        return value
