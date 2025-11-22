import pandas as pd

# Lire le fichier CSV
df = pd.read_csv('LauzHACK/partner.csv')

# Liste des industries suspectes
suspicious_industries = [
    'Investment intermediation',
    'O. financial intermediation n.e.c.',
    'Regulated broker',
    'Other non-life insurance n.e.c.',
    'Act. head offices of o. companies',
    'Management of real estate',
    'Letting of own or leased land',
    'Buying & selling of own real estate',
    'Real estate activities',
    'Accounting, bookkeeping activities',
    'Attorney, notary practice',
    'Creative, arts & entertainment act.',
    'Ma. & assembly of watches & clocks',
    'Food & beverage service activities',
    'Hotels, inns & guesthouses w. rest.',
    'Cult., educ., scient.& research org.'
]

# Ajouter la colonne suspicious_industries
# 1 si industry_gic2_code est dans la liste, 0 sinon
df['suspicious_industries'] = df['industry_gic2_code'].apply(
    lambda x: 1 if x in suspicious_industries else 0
)

# Sauvegarder le fichier
df.to_csv('LauzHACK/partner.csv', index=False)

print(f"Colonne 'suspicious_industries' ajoutée avec succès!")
print(f"Nombre total de lignes: {len(df)}")
print(f"Nombre d'industries suspectes: {df['suspicious_industries'].sum()}")
print(f"\nRépartition des industries suspectes trouvées:")
suspicious_df = df[df['suspicious_industries'] == 1]
if len(suspicious_df) > 0:
    print(suspicious_df['industry_gic2_code'].value_counts())
