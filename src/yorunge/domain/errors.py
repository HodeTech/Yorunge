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
}


class YorungeError(Exception):
    """Safe public failure: never attaches parser input, paths or provider bodies."""

    exit_code = 2

    def __init__(self, code: ErrorCode) -> None:
        self.code = code
        self.message = MESSAGES[code]
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
