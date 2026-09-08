def get_player_link(slug):
    return f'https://www.basketball-reference.com{slug}'

def get_player_headshot(slug):
    jpg = slug.split('/')[-1].replace('.html', '.jpg')
    return f'https://www.basketball-reference.com/req/202106291/images/headshots/{jpg}'
