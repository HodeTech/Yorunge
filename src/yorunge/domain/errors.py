from typing import Literal

ErrorCode = Literal[
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
]

MESSAGES: dict[ErrorCode, str] = {
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
}


class YorungeError(Exception):
    """Safe public failure: never attaches parser input, paths or provider bodies."""

    def __init__(self, code: ErrorCode) -> None:
        self.code = code
        self.message = MESSAGES[code]
        self.exit_code = 3 if code in ("credential_unavailable", "invalid_credential") else 2
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
