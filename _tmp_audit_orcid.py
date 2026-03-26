import pandas as pd
from collections import Counter

df = pd.read_csv('Data/Researchers/cchen_researchers_orcid.csv')

# 1. Sin empleador
sin_emp = df[df['employers'].isna()]
print(f'=== Sin empleador (NaN): {len(sin_emp)} ===')
print(sin_emp[['full_name', 'orcid_works_count']].to_string())

print()

# 2. Con empleadores externos a CCHEN
cchen_keywords = ['cchen', 'comision chilena', 'chilean nuclear', 'nuclear energy commission', 'comisión chilena']
def is_cchen(emp):
    if pd.isna(emp):
        return False
    return any(k in str(emp).lower() for k in cchen_keywords)

df['es_cchen'] = df['employers'].apply(is_cchen)
externos = df[~df['es_cchen'] & df['employers'].notna()]
print(f'=== Empleador NO CCHEN ({len(externos)}) ===')
print(externos[['full_name', 'employers']].to_string(max_colwidth=55))

print()

# 3. Posibles duplicados por apellido
apellidos = df['family_name'].str.strip().str.lower()
dupl = [n for n, c in Counter(apellidos).items() if c > 1 and pd.notna(n)]
print(f'=== Apellidos duplicados: {dupl} ===')
print(df[df['family_name'].str.strip().str.lower().isin(dupl)][['full_name', 'orcid_id', 'employers']].to_string(max_colwidth=45))

print()

# 4. works_count = 0
zeros = (df['orcid_works_count'] == 0).sum()
print(f'=== works_count = 0: {zeros} de {len(df)} ===')

print()

# 5. Resumen
print('=== RESUMEN ===')
print(f'Total registros: {len(df)}')
print(f'Confirmados CCHEN (employer): {df["es_cchen"].sum()}')
print(f'Externos (employer ≠ CCHEN): {len(externos)}')
print(f'Sin employer (NaN): {len(sin_emp)}')
print(f'Con works_count = 0: {zeros}')
print(f'IDs 0009-xxxx (perfiles nuevos): {df["orcid_id"].str.startswith("0009").sum()}')
