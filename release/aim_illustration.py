"""Illustration vectorielle originale du sélecteur anatomique (sans dépendance)."""

import aim_i18n

def draw_operator(canvas, selected, choose):
    canvas.delete("all")
    ink, edge, light, cyan = "#202e3b", "#496071", "#354b5c", "#58e0d0"

    def poly(points, fill=ink, outline=edge):
        return canvas.create_polygon(*points, fill=fill, outline=outline, width=1.2)

    def line(points, fill=edge, width=1):
        canvas.create_line(*points, fill=fill, width=width)

    # Plateau de présentation et repères techniques discrets.
    for x in range(20, 281, 20):
        for y in range(20, 361, 20):
            canvas.create_oval(x, y, x+1, y+1, fill="#24303b", outline="")
    canvas.create_oval(53, 338, 247, 363, fill="#0a1017", outline="#23333e")
    canvas.create_oval(70, 342, 230, 359, outline="#36515c")
    line((150, 12, 150, 352), "#20343e")
    for x, sign in ((20, 1), (280, -1)):
        line((x+18*sign, 42, x, 42, x, 65), "#39505b")
        line((x, 308, x, 331, x+18*sign, 331), "#39505b")

    # Jambes : pantalon segmenté, genouillères et bottes.
    for mirror in (False, True):
        def p(points, fill=ink, outline=edge):
            coords = [(300-x if mirror else x, y) for x, y in points]
            return poly([v for xy in coords for v in xy], fill, outline)
        p([(112, 205), (149, 214), (144, 260), (135, 321), (107, 321), (110, 275), (104, 240)])
        p([(109, 224), (140, 225), (134, 258), (113, 255)], "#293d4b")
        p([(111, 258), (136, 260), (137, 279), (113, 285), (106, 273)], light)
        p([(114, 264), (131, 265), (130, 276), (115, 278)], "#16252f")
        p([(112, 287), (134, 283), (128, 318), (110, 317)], "#263845")
        p([(108, 317), (133, 317), (135, 341), (128, 348), (96, 348), (96, 338), (107, 331)], "#14212c")
        p([(97, 341), (133, 338), (133, 348), (96, 348)], "#0d1720")
        # Manches, plaques d'épaule, avant-bras, gants.
        p([(112, 91), (93, 94), (81, 114), (70, 158), (76, 177), (92, 174), (111, 124)], "#283a48")
        p([(92, 99), (111, 99), (109, 122), (83, 124)], light)
        p([(80, 133), (99, 140), (90, 166), (73, 160)], "#1b2a35")
        p([(74, 165), (91, 170), (85, 205), (70, 210), (65, 197)], "#304553")
        p([(69, 202), (85, 205), (84, 223), (76, 233), (65, 227), (62, 215)], "#14222d")
        p([(65, 210), (78, 211), (79, 222), (67, 222)], "#3b505c")

    # Cou, combinaison et gilet porte-plaques.
    poly((137, 72, 163, 72, 169, 95, 150, 109, 130, 95), "#15232e")
    poly((112, 90, 133, 85, 150, 95, 169, 85, 189, 94, 181, 145,
          175, 192, 184, 221, 157, 231, 150, 220, 141, 231, 105, 222, 120, 182), "#253946")
    poly((120, 96, 133, 92, 137, 129, 120, 136), "#536976")
    poly((165, 93, 179, 97, 179, 136, 163, 129), "#536976")
    poly((123, 109, 177, 109, 182, 143, 174, 170, 124, 170, 117, 143), "#344c5b")
    poly((130, 115, 170, 115, 175, 138, 168, 147, 132, 147, 125, 137), "#263b49")
    line((135, 120, 165, 120), "#63818c", 2)
    for x in (124, 142, 160):
        poly((x, 151, x+15, 151, x+15, 177, x+2, 179), "#1a2d3a")
        line((x+3, 155, x+12, 155), "#68808a", 2)
    for y in (184, 191):
        line((125, y, 175, y), "#526c79", 2)
    poly((115, 199, 182, 199, 182, 210, 115, 210), "#101d27")
    poly((143, 198, 157, 198, 157, 211, 143, 211), "#647d86")
    poly((116, 211, 139, 215, 134, 232, 112, 226), "#304653")

    # Cagoule, casque à facettes et visière.
    poly((130, 40, 169, 40, 173, 66, 165, 81, 151, 88, 136, 81, 128, 65), "#182732")
    poly((127, 44, 130, 27, 142, 19, 161, 19, 173, 30, 177, 49, 167, 54, 134, 54), "#3b5261")
    poly((132, 37, 141, 24, 160, 23, 170, 37), "#506a78")
    poly((125, 45, 178, 45, 176, 53, 128, 54), "#1b2b37")
    poly((132, 54, 169, 54, 166, 65, 135, 65), "#0a171f", "#63818c")
    line((137, 57, 163, 57), "#7faaa9", 2)
    poly((140, 69, 160, 69, 163, 79, 151, 84, 137, 77), "#2d4350")
    line((145, 75, 156, 75), "#637d88")

    positions = {"head": 53, "neck": 91, "chest": 131, "stomach": 183, "pelvis": 216}
    for key, y in positions.items():
        active = key == selected
        tag = "zone_" + key
        # Une grande surface de clic, y compris sur les repères latéraux.
        canvas.create_rectangle(128, y-13, 174, y+13, fill="", outline="", tags=tag)
        if active:
            canvas.create_oval(129, y-21, 171, y+21, outline="#285b61", width=5, tags=tag)
            canvas.create_oval(131, y-19, 169, y+19, outline=cyan, width=1.5, tags=tag)
            line((174, y, 216, y, 223, y-7), cyan)
            canvas.create_text(227, y-9, text=aim_i18n.t("figure.target"), fill=cyan, anchor="w",
                               font=("DejaVu Sans", 7, "bold"))
        canvas.create_oval(146, y-4, 154, y+4, fill=cyan if active else "#78909d", outline="#10232d", tags=tag)
        canvas.tag_bind(tag, "<Button-1>", lambda _, k=key: choose(k))
        canvas.tag_bind(tag, "<Enter>", lambda _: canvas.configure(cursor="hand2"))
        canvas.tag_bind(tag, "<Leave>", lambda _: canvas.configure(cursor=""))
    width, height = max(1, canvas.winfo_width()), max(1, canvas.winfo_height())
    if width > 1 and height > 1:
        scale = min(width/300, height/375)
        canvas.scale("all", 0, 0, scale, scale)
        canvas.move("all", (width-300*scale)/2, (height-375*scale)/2)
