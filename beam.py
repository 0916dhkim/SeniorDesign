from constants import *
from sympy import Eq, Symbol, sqrt, N, Abs
from sympy.solvers.solveset import nonlinsolve
from numpy import nan
import rebar


def doubly_reinforced_area(b, d, d_prime, M_u):
    # Unit conversion.
    M_u *= 12 * 1000  # kip-ft to lb-in

    A_s = Symbol('A_s')
    A_s_prime = Symbol('A_s_prime')
    c = Symbol('c')
    epsilon_s = 0.005  # Find A_s and A_s_prime when epsilon_s is 0.005.
    epsilon_s_prime = Symbol('epsilon_s_prime')

    compression_strain_compatibility = Eq(EPSILON_CU/c, epsilon_s_prime/(c-d_prime))
    tension_strain_compatibility = Eq(EPSILON_CU/c, epsilon_s/(d-c))

    # Assumption 1: d_prime < beta_1*c
    force_eq = Eq(0.85*F_PRIME_C*BETA_1*c*b + (E_S*epsilon_s_prime-0.85*F_PRIME_C)*A_s_prime,  # compression
                  F_Y*A_s)                                                                     # tension
    strength_eq = Eq(0.85*F_PRIME_C*BETA_1*c*b*(d-BETA_1*c/2)                       # concrete compression
                     + (E_S*epsilon_s_prime-0.85*F_PRIME_C)*A_s_prime*(d-d_prime),  # reinforcement compression
                     M_u/0.9)                                                       # required strength

    # Solve.
    solution_set = nonlinsolve([compression_strain_compatibility,
                                tension_strain_compatibility,
                                force_eq,
                                strength_eq],
                               [A_s, A_s_prime, c, epsilon_s_prime])

    if not solution_set.is_EmptySet:
        # Check assumption 1.
        for solution in iter(solution_set):
            if d_prime < BETA_1*solution[2]:
                return solution[0], solution[1]

    # Assumption disagreement.
    # Change assumption.
    # Assumption 1: d_prime >= beta_1*c
    force_eq = Eq(0.85*F_PRIME_C*BETA_1*c*b + E_S*epsilon_s_prime*A_s_prime,  # compression
                  F_Y*A_s)                                                    # tension
    strength_eq = Eq(0.85*F_PRIME_C*BETA_1*c*b*(d-BETA_1*c/2)      # concrete compression
                     + E_S*epsilon_s_prime*A_s_prime*(d-d_prime),  # reinforcement compression
                     M_u/0.9)                                      # required strength

    # Solve.
    solution_set = nonlinsolve([compression_strain_compatibility,
                                tension_strain_compatibility,
                                force_eq,
                                strength_eq],
                               [A_s, A_s_prime, c, epsilon_s_prime])

    if not solution_set.is_EmptySet:
        # Check assumption 1.
        for solution in iter(solution_set):
            if d_prime >= BETA_1*solution[2] and solution[2] > 0:
                return solution[0], solution[1]

    # No solution.
    return nan, nan


def shear_spacing(b, d, h, f_u, V_u):
    # 22.5.6.1
    # Assuming lambda = 1
    if f_u > 0:
        # Compression
        V_c = 2*(1+f_u*1000/2000/b/h)*1.0*sqrt(F_PRIME_C)*b*d
    else:
        # Tension
        V_c = 2*(1+f_u*1000/500/b/h)*1.0*sqrt(F_PRIME_C)*b*d

    # Try #3 stirrups
    d_b = rebar.diameter[3]
    A_v = 2*rebar.area[3]

    # Table 21.2.1
    phi=0.75

    # Unknowns
    s = Symbol('s')
    V_s = Symbol('V_s')

    # 22.5.10.5.3
    vs_eq = Eq(V_s, A_v*F_Y*d/s)
    req_eq = Eq(V_s, V_u/phi-V_c)

    solution_set = nonlinsolve([vs_eq, req_eq], [s, V_s])

    # Check s range.
    if not solution_set.is_EmptySet:
        f_s = V_u*1000/phi/2/A_v
        # 25.2.1
        min_s = max(1, d_b, D_AGG*4/3)
        max_s = min(Abs(15*40000/f_s-2.5*C_C), Abs(12*40000/f_s))
        for solution in iter(solution_set):
            if solution[0] > min_s and solution[0] < max_s:
                return solution[0]
        return max_s



def check_doubly_reinforced_design(b, d, d_prime, A_s, A_s_prime, M_u):
    # Unit conversion.
    M_u = M_u * 12 * 1000

    c = Symbol('c')
    epsilon_s = Symbol('epsilon_s')
    epsilon_s_prime = Symbol('epsilon_s_prime')

    compression_strain_compatibility = Eq(EPSILON_CU/c, epsilon_s_prime/(c-d_prime))
    tension_strain_compatibility = Eq(EPSILON_CU/c, epsilon_s/(d-c))

    # Assumption 1: d_prime < beta_1*c
    # Assumption 2: epsilon_s >= epsilon_y
    force_eq = Eq(0.85*F_PRIME_C*BETA_1*c*b + (E_S*epsilon_s_prime - 0.85*F_PRIME_C)*A_s_prime,  # compression
                  F_Y*A_s)                                                                       # tension

    c_solution_set = nonlinsolve([compression_strain_compatibility,
                                  tension_strain_compatibility,
                                  force_eq],
                                 [c, epsilon_s, epsilon_s_prime])

    # Check assumption 1 & 2.
    assumption_1 = False
    assumption_2 = False
    if not c_solution_set.is_EmptySet:
        for solution in iter(c_solution_set):
            if d_prime < BETA_1*solution[0]:
                assumption_1 = True
            if solution[1] >= EPSILON_Y:
                assumption_2 = True
            if assumption_1 and assumption_2:
                c = solution[0]
                epsilon_s = solution[1]
                epsilon_s_prime = solution[2]
                break

    if not assumption_1 or not assumption_2:
        force_eq = Eq(0.85*F_PRIME_C*BETA_1*c*b
                      + (E_S*epsilon_s_prime - (0.85*F_PRIME_C if assumption_1 else 0))*A_s_prime,
                      (F_Y if assumption_2 else E_S*epsilon_s)*A_s)

        # Alternative solution.
        c_solution_set = nonlinsolve([compression_strain_compatibility,
                                      tension_strain_compatibility,
                                      force_eq],
                                     [c, epsilon_s, epsilon_s_prime])

        # Check alternative assumptions.
        if not c_solution_set.is_EmptySet:
            found_solution = False
            for solution in iter(c_solution_set):
                if not assumption_1 and d_prime < BETA_1*solution[0] or solution[0] < 0:
                    continue
                if not assumption_2 and solution[1] >= EPSILON_Y:
                    continue
                c = solution[0]
                epsilon_s = solution[1]
                epsilon_s_prime = solution[2]
                found_solution = True
                break

            if not found_solution:
                # There is no possible value for c.
                return 0

    # Found c.
    # Check strength.
    phi = min(0.9, 0.65 + (epsilon_s - 0.002) * 250/3)
    return (M_u/phi)/\
           (0.85*F_PRIME_C*BETA_1*c*b*(d-BETA_1*c/2)
            + (E_S*epsilon_s_prime-(0.85*F_PRIME_C if assumption_1 else 0))*A_s_prime*(d-d_prime))
