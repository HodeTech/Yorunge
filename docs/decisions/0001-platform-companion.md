# ADR-0001: EVREN odaklı kapsamlı yardımcı ürün

**Durum:** Accepted. **Tarih:** 2026-10-27. **Dayanak:** Kullanıcının ürün konumlandırması.

## Bağlam

İlk araştırma veri aktarımı, LLM servisleri ve ForgeLM fizibilitesini birlikte ele aldı. Ürünü tek bir eğitim aracının yardımcı akışı olarak anlatmak EVREN'deki veri, katalog, çıkarım, kaynak ve iş yönetimi ihtiyaçlarını eksik temsil ediyor.

## Karar

Yörünge, EVREN platformunun kapsamlı yardımcı aracıdır. Ana kullanıcı görevleri hesap/proje, veri, model/katalog, LLM ve çıkarım, eğitim/değerlendirme, kaynak/kota ve sonuç yönetimini kapsar. İsim Yörünge; teknik kimlik adayı `yorunge` olarak kalır. Özellikler aşamalı teslim edilir.

## Alternatifler

ForgeLM merkezli yan araç dar kapsamlı olduğu için seçilmedi. EVREN'in bütün web arayüzünü yeniden oluşturmak ilk değer için gereksiz maliyet taşır. İlk yüzey CLI/Python'dır; gelecekteki arayüzler aynı iş kurallarına bağlanır.

## Sonuçlar

Ürün ForgeLM kurmadan da değer üretmelidir. Yol haritasında veri ve çıkarım görevleri eğitimden önce veya bağımsız doğrulanır. Daha geniş kapsam, bütün endpointleri aynı sürümde destekleme taahhüdü yaratmaz. Kanonik sınır [ürün kapsamıdır](../product-scope.md).
