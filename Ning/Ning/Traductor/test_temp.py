from translate import translate_ollama

texte = ("People living with mental health conditions often face stigma and "
         "discrimination, which can prevent them from seeking the support and "
         "treatment they need to recover and live fulfilling lives.")

for t in [0.0, 1.0, 2.0]:
    print(f"\n===== Température {t} =====")
    for essai in range(3):
        print(f"[essai {essai+1}] {translate_ollama(texte, temperature=t)}")