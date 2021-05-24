# all imports
import os, math, urllib.request, json
import tweepy
from dotenv import load_dotenv
from PIL import Image, ImageDraw

# username to create interaction circle for
screen_name = 'AniketTeredesai'

# load environment variables
load_dotenv()
APP_KEY = os.environ['API_KEY']
APP_SECRET = os.environ['API_SECRET_KEY']
ACCESS_TOKEN = os.environ['ACCESS_TOKEN']
ACCESS_TOKEN_SECRET = os.environ['ACCESS_TOKEN_SECRET']

# API connection
auth = tweepy.OAuthHandler(APP_KEY, APP_SECRET)
auth.set_access_token(ACCESS_TOKEN, ACCESS_TOKEN_SECRET)
api = tweepy.API(auth, wait_on_rate_limit=True, wait_on_rate_limit_notify=True)

# urllib setup (precaution)
opener=urllib.request.build_opener()
opener.addheaders=[('User-Agent','Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/36.0.1941.0 Safari/537.36')]
urllib.request.install_opener(opener)

def verify_user(screen_name):
    try:
        user = api.get_user(screen_name=screen_name)
        return user
    except tweepy.TweepError as e:
        if e.args[0][0]['code'] == 50:
            print('User Not Found')
            return None
    except:
        print("couldn't connect to the api and verify the screen_name")
        return None

def get_user_avatar(user):
        avatar_url = user.profile_image_url_https.replace('normal', '400x400')
        file, _ = urllib.request.urlretrieve(avatar_url)
        return file

def get_timeline(screen_name):
    res = []
    for page in tweepy.Cursor(api.user_timeline, screen_name=screen_name, count=200).pages(6): #fetches 1200 tweets
        for tweet in page:
            res.append(tweet)
    print('Fetched the entire timeline')
    return res

def get_liked(screen_name):
    res = []
    for page in tweepy.Cursor(api.favorites, screen_name=screen_name, count=200).pages(6):
        for each_like in page:
            res.append(each_like)
    print('Fetched all likes')
    return res

def add_record(user_scores, screen_name, type):
    if screen_name in user_scores.keys():
        user_scores[screen_name][type] +=1
        return user_scores
    else:
        user_scores.update({screen_name: {
            'likes': 0,
            'retweets': 0,
            'replies': 0
        }})
        return user_scores

def get_scores(screen_name):
    timeline = get_timeline(screen_name)
    likes = get_liked(screen_name)
    user_scores = {}
    for tweet in timeline:
        if tweet.in_reply_to_screen_name and tweet.in_reply_to_screen_name != screen_name:
            user_scores = add_record(user_scores, tweet.in_reply_to_screen_name, 'replies')
        if hasattr(tweet, 'retweeted_status') and tweet.retweeted_status.user.screen_name != screen_name:
            user_scores = add_record(user_scores, tweet.retweeted_status.user.screen_name, 'retweets')
    print('calculated replies and retweets')

    for like in likes:
        if like.user.screen_name != screen_name:
            user_scores = add_record(user_scores, like.user.screen_name, 'likes')
    print('calculated likes')
    return user_scores

def select_users(user_scores):
    tmp_dict = {}
    for user in user_scores:
        total = user_scores[user]['likes']*1 + user_scores[user]['replies']*1.1 + user_scores[user]['replies']*1.3
        tmp_dict.update({user: total})
    sorted_dict = dict(sorted(tmp_dict.items(), key=lambda x:x[1]))
    pairs = list(sorted_dict.items())
    selected_users = []
    for i in range(len(pairs)-1, len(pairs)-50, -1):
        selected_users.append(pairs[i])
    print('sorted dict according to the total')
    return dict(selected_users)

def get_selected_avatars(selected_users):
    users_list = [user for user in selected_users.keys()]
    res = api.lookup_users(screen_names=users_list, include_entities=False)
    avatars = {}
    for user in res:
        avatars.update({user.screen_name : user.profile_image_url_https.replace('_normal', '_400x400')})
    print('fetched all avatar urls')
    return avatars

def combine_avatars(selected_users, avatars):
    for user in selected_users:
        selected_users[user] = {
            'score' : selected_users[user],
            'avatar' : avatars[user]
        }
    print('avatar urls added to the selected users dictionary')
    return selected_users

def create_bg():
    mode = 'RGB'
    size = (1000, 1000)
    color = (94, 23, 235)
    bg = Image.new(mode, size, color)
    return bg

def create_mask(image):
    alpha = Image.new('L', image.size, 0)
    draw = ImageDraw.Draw(alpha)
    draw.pieslice([(0, 0), image.size], 0, 360, fill=255)
    return alpha

def create_image(center_avatar, selected_users):
    bg = create_bg()
    users_in_circle={}
    print('created background')
    gap = 10
    layers=[{'image_count': 8, 'radius': 150, 'starting_index': 0, 'ending_index': 8},
            {'image_count': 15, 'radius': 270, 'starting_index': 8, 'ending_index': 23},
            {'image_count': 26, 'radius': 380, 'starting_index': 23, 'ending_index': 60}]
    bg_w, bg_h = bg.size
    center_avatar = Image.open(center_avatar).convert('RGB')
    center_avatar = center_avatar.resize((160, 160))
    bg.paste(center_avatar, ((bg_w - 160)//2, (bg_h - 160)//2), create_mask(center_avatar))
    print('pasted central avatar')
    for layer in layers:
        image_count = layer['image_count']
        gaps_count = image_count-1
        R = layer['radius']
        circuit = 2*math.pi*R
        diagonal = int((circuit - gaps_count*gap) / image_count)
        no_of_image = 0
        base_angle = 360/layer['image_count']
        users_list = []
        for user in selected_users:
            if list(selected_users.keys()).index(user) >= layer['starting_index'] and list(selected_users.keys()).index(user) < layer['ending_index']:
                users_list.append(user)
                file, _ = urllib.request.urlretrieve(selected_users[user]['avatar'])
                avatar = Image.open(file).convert('RGB')
                h = diagonal
                w = diagonal
                avatar = avatar.resize((h, w))
                angle_x = math.cos(math.radians(base_angle*no_of_image))
                angle_y = math.sin(math.radians(base_angle*no_of_image))
                x = math.ceil(R * angle_x + 445) + (layers.index(layer)*8) #offset to address circles misalignment
                y = math.ceil(R * angle_y + 445) + (layers.index(layer)*8) #offset to address circles misalignment
                bg.paste(avatar, (x, y), create_mask(avatar))
                no_of_image += 1
            else:
                pass
        users_in_circle.update({f'circle-{layers.index(layer)}': users_list})
    bg.save(f'{screen_name}.jpg')
    print('image created and saved')
    with open('circles.json', 'w') as f:
        json.dump(users_in_circle, f)
    print('saved the circles, too ;)')

def start(screen_name):
    user = verify_user(screen_name)
    if user != None:
        center_avatar = get_user_avatar(user)
        scores = get_scores(screen_name)
        selected_users = select_users(scores)
        selected_avatars = get_selected_avatars(selected_users)
        selected_users = combine_avatars(selected_users, selected_avatars)
        create_image(center_avatar=center_avatar, selected_users=selected_users)
    else:
        print('quitting...')

start(screen_name)