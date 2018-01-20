---
layout: post
title: Blender API Scripting cheat-sheet
date: 2018-01-10 06:23:00 -0800
categories: Blender Scripting
---


## Things to try in Blender Console or add to scripts


Activate or de-activate 3D View layer


    bpy.data.scenes['Scene'].layers[10] = True
    bpy.data.scenes['Scene'].layers[0] = False

