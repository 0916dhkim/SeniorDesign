import sympy
# Concrete Design Properties
D_AGG = 2
# Table 19.2.1.1
F_PRIME_C = 4000  # psi
# 19.2.1.1
E_C = 57000*sympy.sqrt(F_PRIME_C)
# Table 19.2.4.2
LAMBDA = 1
# 19.2.3.1
F_R = 7.5 * LAMBDA*sympy.sqrt(F_PRIME_C)  # psi
# Section 4-3
# BETA_1 = 0.85 for F_PRIME_C <= 4000 psi
BETA_1 = 0.85
# Maximum useable compression strain in concrete
EPSILON_CU = 0.003

# Reinforcement Design Properties
E_S = 29E6  # psi
F_Y = 60000  # psi
EPSILON_Y = F_Y / E_S
C_C = 2.5  # Concrete cover
