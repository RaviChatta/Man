import pyrogram
from time import time 
from loguru import logger

from pyrogram import idle
import random, os, shutil, asyncio

from pyrogram import utils as pyroutils
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup

class Vars:
  API_ID = int(os.environ.get("API_ID", "25259066"))
  API_HASH = os.environ.get("API_HASH", "caad2cdad2fe06057f2bf8f8a8e58950")
  
  BOT_TOKEN = os.environ.get("BOT_TOKEN", "7617704384:AAFtjQRfvYUO77Be3GPCEWXsmIiQQGVpBR0")
  plugins = dict(
    root="TG",
    #include=["TG.users"]
  )
  
  LOG_CHANNEL = os.environ.get("LOG_CHANNEL", "")
  UPDATE_CHANNEL = os.environ.get("UPDATE_CHANNEL", "@TFIBOTS")
  DB_URL = os.environ.get("DB_URL", "mongodb+srv://senku4:1S1Y7OeNUe9dDs8B@senku.bqs9fgx.mongodb.net/?retryWrites=true&w=majority&appName=senku")
  
  PORT = int(os.environ.get("PORT", "8080"))
  ADMINS = [1047253913]
  
  IS_PRIVATE = os.environ.get("IS_PRIVATE", None) #True Or None  Bot is for admins only
  CONSTANT_DUMP_CHANNEL = os.environ.get("CONSTANT_DUMP_CHANNEL", None)
  WEBS_HOST = os.environ.get("WEBS_HOST", True) # For Render and Koyeb
  
  DB_NAME = "Manhwadb"
  PING = time()
  FORCE_SUB_CHANNEL = os.environ.get("FORCE_SUB_CHANNEL", "")
  SHORTENER = os.environ.get("SHORTENER", None)
  SHORTENER_API = os.environ.get("SHORTENER_API", "") # put {} for url, ex: shornter.api?url={}
  DURATION = int(os.environ.get("DURATION", "20")) # hrs
  PICS = (
    "https://ik.imagekit.io/jbxs2z512/hd-anime-prr1y1k5gqxfcgpv.jpg?updatedAt=1748487947183",
    "https://ik.imagekit.io/jbxs2z512/naruto_GxcPgSeOy.jpg?updatedAt=1748486799631",
    "https://ik.imagekit.io/jbxs2z512/dazai-osamu-sunset-rooftop-anime-wallpaper-cover.jpg?updatedAt=1748488276069",
    "https://ik.imagekit.io/jbxs2z512/thumb-1920-736461.png?updatedAt=1748488419323",
    "https://ik.imagekit.io/jbxs2z512/116847-3840x2160-desktop-4k-bleach-background-photo.jpg?updatedAt=1748488510841",
    "https://ik.imagekit.io/jbxs2z512/images_q=tbn:ANd9GcSjvt9DcrLXzGYEwwOpxwCSFXTfKEhXhVB-Zg&s?updatedAt=1748488611032",
    "https://ik.imagekit.io/jbxs2z512/thumb-1920-777955.jpg?updatedAt=1748488978230",
    "https://ik.imagekit.io/jbxs2z512/thumb-1920-1361035.jpeg?updatedAt=1748488911202",
    "https://ik.imagekit.io/jbxs2z512/akali-wallpaper-960x540_43.jpg?updatedAt=1748489275125",
    "https://ik.imagekit.io/jbxs2z512/robin-honkai-star-rail-497@1@o?updatedAt=1748490140360",
    "https://ik.imagekit.io/jbxs2z512/wallpapersden.com_tian-guan-ci-fu_1920x1080.jpg?updatedAt=17484902552770000",
    "https://ik.imagekit.io/jbxs2z512/1129176.jpg?updatedAt=1748491905419",
    "https://ik.imagekit.io/jbxs2z512/wp14288215.jpg?updatedAt=1748492348766",
    "https://ik.imagekit.io/jbxs2z512/8k-anime-girl-and-flowers-t4bj6u55nmgfdrhe.jpg?updatedAt=1748493169919",
    "https://ik.imagekit.io/jbxs2z512/anime_Fuji_Choko_princess_anime_girls_Sakura_Sakura_Woman_in_Red_mask_palace-52030.png!d?updatedAt=1748493259665",
    "https://ik.imagekit.io/jbxs2z512/1187037bb1d8aaf14a631f7b813296f1.jpg?updatedAt=1748493396756",
    "https://ik.imagekit.io/jbxs2z512/yor_forger_by_senku_07_dgifqh7-fullview.jpg_token=eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJ1cm46YXBwOjdlMGQxODg5ODIyNjQzNzNhNWYwZDQxNWVhMGQyNmUwIiwiaXNzIjoidXJuOmFwcDo3ZTBkMTg4OTgyMjY0MzczYTVmMGQ0MTVlYTBkMjZlMCIsIm9iaiI6W1t7ImhlaWdodCI6Ijw9ODAzIiwicGF0aCI6IlwvZlwvNDAxZDdlYTYtOGEyZi00ZTFiLTkxYTAtNjA3YmRlYTgzZmE4XC9kZ2lmcWg3LWNlMjY3Mzc2LWQ4NWYtNGMzZS1iNWY1LWU0OTZhYWM3ZmUyNC5wbmciLCJ3aWR0aCI6Ijw9MTI4MCJ9XV0sImF1ZCI6WyJ1cm46c2VydmljZTppbWFnZS5vcGVyYXRpb25zIl19.FVwtt0HGKv6UQqWHkEbxmE1qkI5CFNNS5SzAYj4EVUs?updatedAt=1748493490929",
    "https://ik.imagekit.io/jbxs2z512/attack-on-titan-mikasa-cover-image-ybt96t1e1041qdt3.jpg?updatedAt=1748493720903",
    "https://ik.imagekit.io/jbxs2z512/tsunade-at-her-desk-bakoh4jeg42sjn3c.jpg?updatedAt=1748493962363",
    "https://ik.imagekit.io/jbxs2z512/9aab3a2fba4bd0117b990e4ca453cb61.jpg?updatedAt=1748494616359",
    "https://ik.imagekit.io/jbxs2z512/3bf8ed2f8f1acacd5451444ba6e7842a.jpg?updatedAt=1748494817874",
    "https://ik.imagekit.io/jbxs2z512/5f10d5eeab91c46b2b442d170998a10e.jpg?updatedAt=1748494936535",
    "https://ik.imagekit.io/jbxs2z512/18a02ef5ab71d0df7a1b4f854c214dfb.jpg?updatedAt=1748495170887",
    "https://ik.imagekit.io/jbxs2z512/3860e6e91d9cc88b4579d096e4edaaf3.jpg?updatedAt=1748495479043",
    "https://ik.imagekit.io/jbxs2z512/d367f6d6d22f4ead7c359e9f091db94e.jpg?updatedAt=1748495852427",
    "https://ik.imagekit.io/jbxs2z512/9c989e113f6ba997e417a436cde4a387.jpg?updatedAt=1748496068439",
    "https://ik.imagekit.io/jbxs2z512/8750ba474fb938b94d6b1a4093e5c104.jpg?updatedAt=1748496295001",
    "https://ik.imagekit.io/jbxs2z512/2e6937e9d7c6fb4c179c3e92684bb7f4.jpg?updatedAt=1748496479835",
    "https://ik.imagekit.io/jbxs2z512/99ce9434aed7b5785cae1d784aee3d72.jpg?updatedAt=1748497104463",
    "https://ik.imagekit.io/jbxs2z512/stycc.jpg?updatedAt=1748497475612",
    "https://ik.imagekit.io/jbxs2z512/9bba360ebd71d6086e19d5729b80a5b8.jpg?updatedAt=1748497751053",
    "https://ik.imagekit.io/jbxs2z512/94f23c5b9055846db8047565bbb8cd70.jpg?updatedAt=1748497975473",
    "https://ik.imagekit.io/jbxs2z512/eec7ff7238553179fb4236da3537d19d.jpg?updatedAt=1748498058373",
    "https://ik.imagekit.io/jbxs2z512/Fight-Break-Sphere.png?updatedAt=1750042299023",
    "https://ik.imagekit.io/jbxs2z512/doupocangqiong-medusa-queen-hd-wallpaper-preview.jpg?updatedAt=1750042397343",
    "https://ik.imagekit.io/jbxs2z512/wp5890248.jpg?updatedAt=1750042498187",
    "https://ik.imagekit.io/jbxs2z512/sacffc_uu-T1F5AC?updatedAt=1750042873876",
    "https://ik.imagekit.io/jbxs2z512/1345216.jpeg?updatedAt=1750042982858",
    "https://ik.imagekit.io/jbxs2z512/shanks-divine-departure-attack-in-one-piece-sn.jpg?updatedAt=1750043121252",
    "https://ik.imagekit.io/jbxs2z512/1a74aff1d81a1af5f3e25b9b30282e06.jpg?updatedAt=1750043251516",
    "https://ik.imagekit.io/jbxs2z512/a7241b95829a685f99a900e509e39591.jpg?updatedAt=1750043398842",
    "https://ik.imagekit.io/jbxs2z512/2dff5d8b43c34b8bdc6b2064e0917123_low.webp?updatedAt=1751077578776",
    "https://ik.imagekit.io/jbxs2z512/1217847739e4bf310076a217bb4c4762_low.webp?updatedAt=1751077642452",
    "https://ik.imagekit.io/jbxs2z512/44ba8229f62d7f7b9251ff8839a1d8ea_low.webp?updatedAt=1751077714921",
    "https://ik.imagekit.io/jbxs2z512/a6d39692ba169fc142a410995878408d_low.webp?updatedAt=1751077802364",
    "https://ik.imagekit.io/jbxs2z512/367c7d7031988b2b06a56e7096a734153fab2284_low.webp?updatedAt=1751077891589",
    "https://ik.imagekit.io/jbxs2z512/22219.jpg?updatedAt=1751107408410",
    "https://ik.imagekit.io/jbxs2z512/21418.jpg?updatedAt=1751107452919",
    "https://ik.imagekit.io/jbxs2z512/mythical-dragon-beast-anime-style_23-2151112835.jpg?updatedAt=1751107574210",
    "https://ik.imagekit.io/jbxs2z512/halloween-scene-illustration-anime-style_23-2151794288.jpg?updatedAt=1751107676806",
    "https://ik.imagekit.io/jbxs2z512/5823589-2920x1640-desktop-hd-boy-programmer-wallpaper-image.jpg_id=1726666227?updatedAt=1751107911063",
    "https://ik.imagekit.io/jbxs2z512/thumbbig-1345576.webp?updatedAt=1751108065802",
    "https://ik.imagekit.io/jbxs2z512/thumb-440-1340473.webp?updatedAt=1751108159970",
    "https://ik.imagekit.io/jbxs2z512/thumb-440-1250445.webp?updatedAt=1751108243962",
    "https://ik.imagekit.io/jbxs2z512/wp3084738.jpg?updatedAt=1751108326075",
    "https://ik.imagekit.io/jbxs2z512/wp12362449.png?updatedAt=1751108554882",
    "https://ik.imagekit.io/jbxs2z512/wp7627005.jpg?updatedAt=1751108634878",
    "https://ik.imagekit.io/jbxs2z512/thumbbig-1335194.webp?updatedAt=1751108710765",
    "https://ik.imagekit.io/jbxs2z512/thumbbig-1373976.webp?updatedAt=1751108748746",
    "https://ik.imagekit.io/jbxs2z512/thumbbig-1065277.webp?updatedAt=1751108877871",
    "https://ik.imagekit.io/jbxs2z512/thumbbig-877141.webp?updatedAt=1751108916209",
    "https://ik.imagekit.io/jbxs2z512/thumbbig-856517.webp?updatedAt=1751108984376",
    "https://ik.imagekit.io/jbxs2z512/thumbbig-722181.webp?updatedAt=1751109016670",
    "https://ik.imagekit.io/jbxs2z512/thumbbig-1337392.webp?updatedAt=1751109084903",
    "https://ik.imagekit.io/jbxs2z512/anime-4k-pc-hd-download-wallpaper-preview%20(1).jpg?updatedAt=1751109522060",
    "https://ik.imagekit.io/jbxs2z512/876145-3840x2160-desktop-4k-konan-naruto-background-image%20(1).jpg?updatedAt=1751109523353",
    "https://ik.imagekit.io/jbxs2z512/tumblr_9663cff78634f174f81b41b64fc450df_66ebd999_1280%20(1).png?updatedAt=1751109523759",
    "https://ik.imagekit.io/jbxs2z512/anime-girl-demon-horn-art-4k-wallpaper-uhdpaper.com-714@2@b%20(1).jpg?updatedAt=1751109524369",
    "https://ik.imagekit.io/jbxs2z512/wp14771453.png?updatedAt=1751110776400",
    "https://ik.imagekit.io/jbxs2z512/dbbb586df338d55d340ec650bcdd74fe.jpg?updatedAt=1751110984735",
    "https://ik.imagekit.io/jbxs2z512/5bf388947f00a495089a892729e30eff.jpg?updatedAt=1751111093184",
    "https://ik.imagekit.io/jbxs2z512/70c6b3a1007864c703eee8161de10b16.jpg?updatedAt=1751111171988",
    "https://ik.imagekit.io/jbxs2z512/8f27da8d6616d8f80af36c8b765a149b.jpg?updatedAt=1751111431360",
    "https://ik.imagekit.io/jbxs2z512/2bbc87d73d2aeefb70c5ab9cc7f5d9d4.jpg?updatedAt=1751111480775",
    "https://ik.imagekit.io/jbxs2z512/1fa6825ca849a55808e112371721cfe4.jpg?updatedAt=1751111592964",
    "https://ik.imagekit.io/jbxs2z512/67a32939a3510571e08ef949ac9209e6.jpg?updatedAt=1751111647854",
    "https://ik.imagekit.io/jbxs2z512/a5f26efcc42a213a64eda0a2a15fc26c.jpg?updatedAt=1751111705093",
    "https://ik.imagekit.io/jbxs2z512/4d8f713943c109c88130118b12803cc7.jpg?updatedAt=1751111768586",
    "https://ik.imagekit.io/jbxs2z512/c02aecb70c3c6a5b1f51ba09e4d2cc70.jpg?updatedAt=1751111979586",
    "https://ik.imagekit.io/jbxs2z512/6c2618a1eea58d22e2d1a5ba99c95a1c.jpg?updatedAt=1751112051082",
    "https://ik.imagekit.io/jbxs2z512/7a82750e26bf451ab1775993279e2c64.jpg?updatedAt=1751112189297",
    "https://ik.imagekit.io/jbxs2z512/a469262476f60456dd4aceb8a75deed5.jpg?updatedAt=1751112263336",
     "https://telegra.ph/file/4414fb4d9e5fc36b65dc3-226143890200f06482.jpg",
    "https://telegra.ph/file/5e8d5c2ffbca4b9fa8c55-2b761e82504f6d8775.jpg",
    "https://telegra.ph/file/66c4adb1cf48ad68f3e31-81b19189a88625a39d.jpg",
    "https://telegra.ph/file/917c9567c4bb6da7c6db8-f7339d7b2e93398c8d.jpg",
    "https://telegra.ph/file/e7d8001a5813aa0bf8cef-f1ea2f9acd19c8c33b.jpg",
    "https://telegra.ph/file/415824c578ecf968a0c97-415f6bd1d2f2288c37.jpg",
    "https://telegra.ph/file/145eb941c14244ba7d25d-8cc9e293f41a01e04a.jpg",
    "https://telegra.ph/file/7388e3b2d3578ca9b596b-ae32749fd31e3f5bc0.jpg",
    "https://telegra.ph/file/0b7be04643304a2ebcc6c-0587c187997cf914a7.jpg",
    "https://telegra.ph/file/3f5e586ea5bbec365d779-0dedabf922fe53e191.jpg",
    "https://telegra.ph/file/c94cffc02557fb0f11098-69ea5789dd37e12834.jpg",
    "https://telegra.ph/file/5d79104e8468436552663-2bcd118f9816175500.jpg",
    "https://telegra.ph/file/479b4d3467abf19b6b7a8-79e46663286d728dbc.jpg",
    "https://telegra.ph/file/69e42d76add43f00c55ab-e7276303644245a02b.jpg",
    "https://telegra.ph/file/5cd3f2dd31d0c104d738f-b5176fcaaf1d27c86b.jpg",
    "https://telegra.ph/file/8aea25f56068077fb9a6e-7c3196d90da6c4c137.jpg",
    "https://telegra.ph/file/e91f8620c6042c521b624-5c66a3ccffd8b58b35.jpg",
    "https://telegra.ph/file/59e48aaffa4f757f9c91d-266c89b777ae2c1f9c.jpg",
    "https://telegra.ph/file/0bed23372a01242cc4bd5-119156af63830625cf.jpg",
    "https://telegra.ph/file/7baf42b4bf222dfa8397f-8539ff06db4ae8af3f.jpg",
    "https://telegra.ph/file/a43b2e1935d6c3afadb05-3efb6228df4c8adfaa.jpg",
    "https://telegra.ph/file/703cac9dc03549c0e86d5-6975e10193fbe45a01.jpg",
    "https://telegra.ph/file/e8effd37463cac5087133-4ed8bde82c6537edfa.jpg",
    "https://telegra.ph/file/617b82cf932512af1c418-c82535ace2753cb4c6.jpg",
    "https://telegra.ph/file/bf050a785e9777c7b999b-80b87ca2b0b9af4591.jpg",
    "https://telegra.ph/file/a9916e4561bb1ade528bd-fef1aaa186f0714005.jpg",
    "https://telegra.ph/file/0c807d34c9f3ef5cd5e3e-0830fca9a852b068f5.jpg",
    "https://telegra.ph/file/f8eefbda1f3d3e87d8565-3679d05921b1cbfd65.jpg",
    "https://telegra.ph/file/7a5c115fae6a6bcd1a681-c1d20a8d1ecc737d34.jpg",
    "https://telegra.ph/file/a92688b73fc89de2fc153-0883dcd1a567ec166e.jpg",
    "https://telegra.ph/file/7245907ecd1d5e32863cb-b99b8c5e963cc68324.jpg",
    "https://telegra.ph/file/8396534567bfaee71574f-bf7a419d673fe97bb2.jpg",
    "https://telegra.ph/file/63f8c0e0cd763be4dc204-cff77323f000112b96.jpg",
    "https://telegra.ph/file/8f65f3de13499c07e83bb-e854395ff12cb99fde.jpg",
    "https://telegra.ph/file/e56d10f3a526cd74a5d9d-90c76937bfbdf72c97.jpg",
    "https://telegra.ph/file/f4603e9c4266640e79678-7af3ebbabc913c7a02.jpg",
    "https://telegra.ph/file/aeb6851cf9cd86017d861-3ce10b0c32acd81045.jpg",
    "https://telegra.ph/file/2fc3974226c01fa438f4b-9b046d82bf8cd60efe.jpg",
    "https://telegra.ph/file/d5f3de3ec8f2bf7e06eaf-711b48e815e351ab1e.jpg",
    "https://telegra.ph/file/de276b83a9db197110b01-e8fd8829ec4af1b590.jpg",
    "https://telegra.ph/file/cce259cca9ffdef0695b0-75ca0212bb82496e30.jpg",
    "https://telegra.ph/file/de2a020446f873f451131-ac9f9e028b637a3c68.jpg",
    "https://telegra.ph/file/7595bc5e1c8cf57c9abd8-8ec90dd444fcf370c9.jpg",
    "https://telegra.ph/file/b0225917b1986dcc1dee2-da7a59f81124cd6e7a.jpg",
    "https://telegra.ph/file/88c8a15550365a7666aff-0cec62df3b958efd2a.jpg",
    "https://telegra.ph/file/bb0cec3364900a5d19fe3-9b52048d73468da45b.jpg",
    "https://telegra.ph/file/ab8c5167306854885712a-4699a010e442672ef0.jpg",
    "https://telegra.ph/file/0e1d1fb09336ce4472e94-c3232af883ea4b05c7.jpg",
    "https://telegra.ph/file/5e26db36ad034591914e1-196f8e52b1095f9eef.jpg",
    "https://telegra.ph/file/7e6e5f45dc78eca2d7ed2-badb68be7337c3082a.jpg",
    "https://telegra.ph/file/7441eb83ed69c2cc7299c-9dcada3341f57087b7.jpg",
    "https://telegra.ph/file/11e041620b9da13b94298-af0d1aae75c15f8517.jpg",
    "https://telegra.ph/file/8f5fb15110c8f4671e541-5999f0ad11af309726.jpg",
    "https://telegra.ph/file/895acbe821a7511ce323f-8f688f28f93e108cb3.jpg",
    "https://telegra.ph/file/313e4bbdbe6d8824dc722-e3520e8b91b70b6b6c.jpg",
    "https://telegra.ph/file/2709c5177c28477534bd7-1a64cf7d2c5196129a.jpg",
    "https://telegra.ph/file/edfc82724b2f0912a93b7-9a4c4c3ebc4f3763a6.jpg",
    "https://telegra.ph/file/47b9697c4ea307838adc1-8107ab2ffcc99e2e0c.jpg",
    "https://telegra.ph/file/5e7bec9860f32de495359-7e1349358df4e424ec.jpg",
    "https://telegra.ph/file/6ead9daabe54b91eab70a-5b3efb4222f8b6f747.jpg",
    "https://telegra.ph/file/466843b5cc6f5b85bd11e-6a306998514b84cb50.jpg",
    "https://telegra.ph/file/56dd0e678321b52d06a30-7e318251ff5a360fe8.jpg",
    "https://telegra.ph/file/627cd31179d8d02386e91-ef43b6f461362cbf8c.jpg",
    "https://telegra.ph/file/657602b7674627b13fa84-c1ba88aca3f1a3b2c9.jpg",
    "https://telegra.ph/file/5f427fddfa0b02d266f49-b66f03a52b605fd06c.jpg",
    "https://files.catbox.moe/3mtgb2.jpg",
    "https://files.catbox.moe/yly8lj.jpg",
    "https://i.ibb.co/N6rTvZXG/x.jpg",
    "https://i.ibb.co/pB8SMVfz/x.png",
    "https://i.ibb.co/F4ytZfyG/x.jpg",
    "https://files.catbox.moe/12x54p.jpg",
    "https://files.catbox.moe/gknros.jpg",
    "https://files.catbox.moe/hbxlc5.jpg",
    "https://files.catbox.moe/vyro5k.jpg",
    "https://files.catbox.moe/amw0s9.jpg",
    "https://files.catbox.moe/grdfu6.jpg",
    "https://files.catbox.moe/0c3vdv.jpg",
    "https://files.catbox.moe/j5jj97.jpg",
    "https://files.catbox.moe/dp11qk.jpg",
    "https://files.catbox.moe/6xvysm.jpg",
    "https://files.catbox.moe/naahka.jpg",
    "https://files.catbox.moe/k3gmp4.jpg",
    "https://files.catbox.moe/wwvshg.jpg",
    "https://files.catbox.moe/roj8a1.jpg",
    "https://files.catbox.moe/0z4rcb.jpg",
    "https://files.catbox.moe/0hvbzu.jpg",
    "https://files.catbox.moe/ooziqn.jpg",
    "https://files.catbox.moe/oglgps.jpg",
  )



pyroutils.MIN_CHAT_ID = -99999999999999
pyroutils.MIN_CHANNEL_ID = -100999999999999

class Manhwa_Bot(pyrogram.Client, Vars):
  def __init__(self):
    super().__init__(
      "ManhwaBot",
      api_id=self.API_ID,
      api_hash=self.API_HASH,
      bot_token=self.BOT_TOKEN,
      plugins=self.plugins,
      workers=50,
    )
    self.logger = logger
    self.__version__ = pyrogram.__version__
    
  async def start(self):
    await super().start()
    
    async def run_flask():
      cmds = ("gunicorn", "app:app")
      process = await asyncio.create_subprocess_exec(
        *cmds,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
      )
      stdout, stderr = await process.communicate()

      if process.returncode != 0:
        logger.error(f"Flask app failed to start: {stderr.decode()}")
      
      logger.info("Webs app started successfully")
    
    usr_bot_me = await self.get_me()
    
    if os.path.exists("restart_msg.txt"):
      with open("restart_msg.txt", "r") as f:
        chat_id, message_id = f.read().split(":")
        f.close()

      try: await self.edit_message_text(int(chat_id), int(message_id), "<code>Restarted Successfully</code>")
      except Exception as e: logger.exception(e)

      os.remove("restart_msg.txt")
    
    if os.path.exists("Process"):
      shutil.rmtree("Process")
    
    self.logger.info("""
    

    _____ ______  _____  ______  _____  _____  _____ 
    |_   _||  ___||_   _| | ___ \|  _  ||_   _|/  ___|
      | |  | |_     | |   | |_/ /| | | |  | |  \ `--. 
      | |  |  _|    | |   | ___ \| | | |  | |   `--. \
      | |  | |     _| |_  | |_/ /\ \_/ /  | |  /\__/ /
      \_/  \_|     \___/  \____/  \___/   \_/  \____/ 
                                                      
                                                      


    """)
    self.username = usr_bot_me.username
    self.logger.info("Made By https://t.me/TFIBOTS")
    self.logger.info(f"Manhwa Bot Started as {usr_bot_me.first_name} | @{usr_bot_me.username}")
    
    if self.WEBS_HOST:
      await run_flask()
    
    MSG = "<blockquote><b>📚 Manga Bot Online! Ready to fetch your favorite manga in a snap. Let’s dive into the pages!</b></blockquote>"

    PICS = random.choice(Vars.PICS)
    
    button = [[
      InlineKeyboardButton('*Start Now*', url= f"https://t.me/{usr_bot_me.username}?start=start"),
      InlineKeyboardButton("*Channel*", url = f"https://t.me/TFIBOTS")
    ]]
    
    try: await self.send_photo(self.UPDATE_CHANNEL, photo=PICS, caption=MSG, reply_markup=InlineKeyboardMarkup(button))
    except: pass

    
  async def stop(self):
    await super().stop()
    self.logger.info("Manhwa Bot Stopped")


Bot = Manhwa_Bot()
    
