---
name: yorunge-verify
description: Yörünge değişikliği için yerel test, belge/skill denetimi, build/temiz kurulum veya performans kontrollerini seç ve gerçek sonucu raporla. Kod yazmak, canlı EVREN deneyi yapmak veya yayınlamak için kullanma.
---
# Yörünge değişikliğini doğrula

[CONTRIBUTING doğrulama matrisi](../../../CONTRIBUTING.md#doğrulama-seçimi) komutların tek kaynağıdır. Repo kökünü ve kurulu interpreter/import kökenini doğrula; başka checkout veya global paketle alınmış sonucu bu değişikliğe yazma.

1. Değişen davranışa uygun kontrolü seç: metin, ajan materyali, runtime, paket veya başlangıç/aktarım bütçesi. Zaten aynı içerik üzerinde geçmiş doğrulamayı sırf listeyi doldurmak için tekrarlama; CI kendi kapısını ayrıca çalıştırır.
2. Başarısızlığı düzelt veya gerçek sınır olarak raporla. Kontrolü skip/xfail yapmak, eşiği gevşetmek veya hatayı yutmak başarılı doğrulama değildir.
3. Testler çevrimdışı/sentetik kalmalı. Gerçek EVREN hesabı, veri aktarımı, GPU işi veya haricî araç kurulumu için bu skill yeni yetki sağlamaz.
4. Paket değişikliğinde wheel/sdist üyelerini ve temiz venv import/konsol kökenini denetle. Ajanın CLI'dan kaynak import etmesi, kurulan artefaktın doğru olduğuna tek başına kanıt değildir.
5. Performansta standarttaki örnek sayısı, ortam ve p95 yöntemini kullan; ilk süreç ölçümünü OS cache'i boşaltılmış fiziksel soğuk başlangıç diye anlatma. Aktarım yoksa RSS/eşzamanlılık kabulünü yapılmış gösterme.

Çıktı: geçen, kalan/başarısız ve çalıştırılmayan kontroller; komut/ortam ve kanıt yeri. İlgili kartın `verified` kararı ancak kendi kabul ölçütleri sağlanınca verilir. Metadata ve link doğrulaması, modelin skill'i gerçekten doğru seçtiği veya canlı API'nin uyduğu anlamına gelmez.
