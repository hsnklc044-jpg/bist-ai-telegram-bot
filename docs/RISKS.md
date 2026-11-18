# Risk kaydı ([CHARTER_2028](CHARTER_2028.md) §5)

İlk kayıt: 18.11.2026, koordinatör. Kayıt çeyrekte bir gözden geçirilir; ilk gözden geçirme 31.12.2026.

Olasılık ve etki ilk değerlendirmedir (Düşük / Orta / Yüksek). Kaynakları kanıt sütununda yazılıdır.

| # | Risk | Olasılık | Etki | Erken uyarı işareti | Önlem (bugün) | Sorumlu | Kanıt |
|---|---|---|---|---|---|---|---|
| R1 | Veri kaynağının kapanması | Orta | Yüksek | Yahoo hata oranı artar; Borsa İstanbul aylık dosyası gecikir | İkinci kaynak Borsa İstanbul resmî gün sonu (K-84, K-93 (3), K-97); Yahoo gecikirse "yalnız bilgi" mesajı (OPERATIONS §8) | Claude izler, kaynak kararı kullanıcının | İş Yatırım 12.11'de kapandı (D13) |
| R2 | Bağımlılıkların eskimesi | Orta | Orta | Python ya da paket destek tarihi yaklaşır; CI uyarıları | Süresi dolan şeyler 30 gün önceden uyarılır (`test_health_ops`, S3_MUDAHALE R8) | Claude | MATURITY S3 satır 2 |
| R3 | Model ya da kota değişiklikleri | Orta | Orta | Haftalık kullanım %70'i geçer; robot turları yarım kalır | Robot %70'te durur; işler küçük paketlere bölünür | Claude raporlar, plan kararı kullanıcının | 11–16.11 kota modu (bellek) |
| R4 | Tek bilgisayara bağımlılık | Yüksek | Yüksek | Pil, uyku, Windows Update yeniden başlatması, disk dolması | Yedek OneDrive'a; geri yükleme testi; dışarıdan izleme (Healthchecks); oturumsuz başlatma taslağı | Kullanıcı (donanım, sistem ayarı), Claude (kayıt, taslak) | `docs/S3_MUDAHALE.md`, `docs/S3_OTURUMSUZ_BASLATMA.md`, K-89 |
| R5 | Aşırı uydurma ve çoklu test yanılgısı | Orta | Yüksek | Ön kayıtsız deneme; deneme sayısının artması; holdout'a erken bakış | `on-kayit` skill'i; deneme sayısı DECISIONS'ta; holdout 27.04.2027'ye kadar kapalı | Claude uygular, eşik ve ön kayıt onayı kullanıcının | K-93, 2027 planı Aşama 2 |
| R6 | Kullanıcının zamanının azalması | Orta | Orta | Onay bekleyen konular 48 saati geçer; haftalık kullanıcı süresi 15 dakikayı aşar | Robot turları; "Senden beklenen" satırı; 48 saat bildirimi (Aralık planı) | Claude ölçer ve sadeleştirme önerir | — |
| R7 | Düzenleyici çerçevenin değişmesi | Düşük | Orta | SPK ya da Borsa İstanbul veri kullanım koşullarında değişiklik | Kapsam dışı: başkasına sinyal, tavsiye ya da abonelik yok; veri kişisel kullanımda (DATA_SOURCES) | Kullanıcı | CHARTER_2028 §2 |
| R7a | Gelir hedefinin SPK lisans sınırına girmesi | Orta | Çok yüksek | Sinyal, tavsiye, abonelik ya da kopyalama özelliğinin başkasına sunulması (ücretli ya da ücretsiz, düzenli) | K-109: gelir modeli düşünülmeden önce avukat görüşü ve sahibin yazılı kapsam kararı; o güne kadar kapsam dışı (CHARTER_2028 §2) | Kullanıcı | SPKn md. 37, 39, 109/2; Tebliğ III-37.1 md. 45–46 |
| R7b | Veri şartlarının gelir hedefiyle çelişmesi | Yüksek (gelir başlarsa) | Yüksek | Yahoo şartları otomatik toplamayı izinsiz yasaklıyor (AUDIT D15); K-54 kabulü yalnız kişisel, ticari olmayan kullanım için | K-109: gelire yönelik ilk adımdan önce lisanslı ya da ticari kullanıma izinli bir veri kaynağı; TCMB verisi için de ticari kullanım izni (DATA_SOURCES) | Kullanıcı | DATA_SOURCES, AUDIT D15 |
