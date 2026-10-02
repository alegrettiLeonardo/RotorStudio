# I14 — explicit motor half-coupling declaration

API 541 lateral-dynamics input includes the motor half-coupling contribution
when applicable. The historical ST41 iRdin file does not identify one of its
`[Massas]` rows as the motor half coupling with sufficient authority.

I14 therefore forbids inference.

Two explicit states are supported:

- `PASS_I14_EXPLICIT_HALF_COUPLING`: one `HalfCoupling` entity is declared
  with node, mass, diametral inertia and polar inertia;
- `NOT_APPLICABLE_I14_EXPLICIT`: an engineering declaration states that no
  separate motor half coupling belongs to the assessed scope, with a required
  textual justification.

An undeclared imported project remains `half_coupling = NOT_DECLARED`.

When present, the half coupling is converted to an inertial disk only inside
the qualified iRdin I9 expanded assembly. It is also included in the two-support
static reaction calculation used by I12. It is not copied into the imported
`[Massas]` list and is never double counted.

I14 by itself does not promote the imported project beyond
`LEGACY_NUMERIC_READY`; API 541 lateral readiness requires a valid I14
declaration plus the I12/I13 gates.
