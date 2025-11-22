import pandas as pd

# Lire le fichier CSV
df = pd.read_csv('LauzHACK/partner_country.csv')

# Ajouter la colonne suspect_country
# 1 si country_name est Panama ou China, 0 sinon
df['suspect_country'] = df['country_name'].apply(
    lambda x: 1 if x in ['Panama', 'China'] else 0
)

# Sauvegarder le fichier
df.to_csv('LauzHACK/partner_country.csv', index=False)

print(f"Colonne 'suspect_country' ajoutée avec succès!")
print(f"Nombre total de lignes: {len(df)}")
print(f"Nombre de pays suspects (Panama ou China): {df['suspect_country'].sum()}")
