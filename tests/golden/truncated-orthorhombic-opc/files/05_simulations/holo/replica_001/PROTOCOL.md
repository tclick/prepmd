# Simulation Protocol Overview

## 01_minimization
- **01_full_restraint**: restraint=10 kcal/mol/Å²; Protein heavy atoms restrained
- **02_backbone_restraint**: restraint=5 kcal/mol/Å²; Backbone restrained
- **03_no_restraint**: restraint=0 kcal/mol/Å²; No positional restraints

## 02_heating
- **02_heating**: restraint=5 kcal/mol/Å²; NVT heating from 0 K to 300.0 K

## 03_equilibration
- **01_5kcal**: restraint=5 kcal/mol/Å²; NPT tapered equilibration
- **02_2kcal**: restraint=2 kcal/mol/Å²; NPT tapered equilibration
- **03_1kcal**: restraint=1 kcal/mol/Å²; NPT tapered equilibration
- **04_0.1kcal**: restraint=0.1 kcal/mol/Å²; NPT tapered equilibration
- **05_0kcal**: restraint=0 kcal/mol/Å²; NPT tapered equilibration

## 04_production
- **run_001**: restraint=0 kcal/mol/Å²; 100-ns production segment
- **run_002**: restraint=0 kcal/mol/Å²; 100-ns production segment
- **run_003**: restraint=0 kcal/mol/Å²; 100-ns production segment
