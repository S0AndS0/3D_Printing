---
layout: post
title: Setting 3D Printer Filament Diameter
date: 2017-12-21 22:51:31 -0800
categories: 3D-Printing-Tips
---

Using digital calipers measure the diameter of the filament six to ten times from
 multiple locations along the filament's length and input the average into the
 slicer's settings.


> **Example:** If using filament advertised as 1.75mm diameter, physical
> measurements may return; 1.77, 1.75, 1.9, 1.87, 1.81, 1.79
> Taking the sum of all measurements and dividing by the number of measurements
> taken...


    (1.77 + 1.75 + 1.9 + 1.87 + 1.81 + 1.79) / 6


> ...would then result in an average diameter of 1.772mm to be input for
> a slicing setting or configuration.


Simple Bash script for calculating filament diameter averages


    #!/usr/bin/env bash
    ## filament-diameter-calc.sh by S0AndS0
    Var_inputed_diameters="${@}"
    Var_arg_length="${#@}"
    Var_avarage_calc="(${Var_inputed_diameters// /+})/${Var_arg_length}"
    case "${Var_inputed_diameters}" in
            help|--help|-h)
                    echo "# Usage: ${0##*/} num1 num2 num3 ..."; exit 0
            ;;
    esac
    Var_avarage_bc="$(echo "scale=3; ${Var_avarage_calc}" | bc)"
    echo "# Avaraging: (${Var_inputed_diameters// /+})/${Var_arg_length}"
    echo "${Var_avarage_bc}"



