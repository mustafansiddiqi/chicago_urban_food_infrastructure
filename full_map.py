legend_html_sections = []

if show_ecosystem:
    ecosystem_section = '<strong>Ecosystem Sites</strong><br>'
    ecosystem_section += f'<i style="background:orange; width:10px; height:10px; float:left; margin-right:6px;"></i> Ecosystem Sites<br><br>'
    legend_html_sections.append(ecosystem_section)

if show_farmers:
    farmers_section = '<strong>Farmers Markets</strong><br>'
    for support_type, color in dcase_color.items():
        if support_type in selected_dcase:
            farmers_section += f'<i style="background:{color}; width:10px; height:10px; float:left; margin-right:6px;"></i> {support_type}<br>'
    farmers_section += '<br>'
    legend_html_sections.append(farmers_section)

if show_snap:
    snap_section = '<strong>Grocery Stores</strong><br>'
    for store_type in selected_store_types:
        color = snap_colors.get(store_type, "black")
        snap_section += f'<i style="background:{color}; width:10px; height:10px; float:left; margin-right:6px;"></i> {store_type}<br>'
    snap_section += '<br>'
    legend_html_sections.append(snap_section)

if show_taverns:
    tavern_section = '<strong>Food Establishments</strong><br>'
    for license_type in selected_tavern_types:
        color = license_colors.get(license_type, "black")
        tavern_section += f'<i style="background:{color}; width:10px; height:10px; float:left; margin-right:6px;"></i> {license_type}<br>'
    tavern_section += '<br>'
    legend_html_sections.append(tavern_section)

if legend_html_sections:
    legend_html = f"""
    <div style="
        position: fixed;
        bottom: 50px;
        right: 50px;
        z-index: 9999;
        background-color: white;
        padding: 10px;
        border: 2px solid black;
        border-radius: 8px;
        box-shadow: 2px 2px 5px rgba(0,0,0,0.3);
        font-size: 13px;
        max-width: 250px;
    ">
        {''.join(legend_html_sections)}
        <div style="clear: both;"></div>
    </div>
    """
    base_map.get_root().html.add_child(Element(legend_html))
