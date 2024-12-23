import pandas as pd
from datetime import date
import datetime as dt
import requests
import os
import time
import utils.cm

pd.set_option('display.max_columns', None)

# specify base path string
basePathStr = './data/dex_decred_org'

# check if path exists, if not create
if not os.path.exists(basePathStr):
    os.makedirs(basePathStr)

# get today's date for file path
todayStr = str(date.today())
yearMonthStr = date.today().strftime("%Y/%m/")


# grab server configuration
configUrl = "https://dex.decred.org/api/config"
response = requests.get(configUrl)
data = response.json()
# extract asset list
assets = pd.json_normalize(data['assets']).set_index('id')
# extract markets list
markets = pd.DataFrame.from_dict(data['markets'])
# replace base with strings
markets['base'] = markets['base'].apply(lambda x: assets.loc[x].symbol)
# replace quote with strings
markets['quote'] = markets['quote'].apply(lambda x: assets.loc[x].symbol)
# path for saving the data
pathStr = basePathStr + '/markets/' + yearMonthStr
if not os.path.exists(pathStr):
    os.makedirs(pathStr)
filename = pathStr + todayStr + '.csv'
# save to csv
markets.to_csv(filename,index=False)


for index, row in assets.iterrows():
    xSymbol = row['unitinfo.conventional.unit']
    dYday = pd.to_datetime(dt.date.today() - dt.timedelta(days=1), utc=True, format='%Y-%m-%dT%H:%M:%S', errors='ignore')
    PriceUSD = utils.cm.getMetric(xSymbol,'ReferenceRateUSD',dYday,dYday)
    assets.at[index, 'ReferenceRateUSD'] = PriceUSD['ReferenceRateUSD'][0]

# grab spots data
del data, response
spotsUrl = "https://dex.decred.org/api/spots"
response = requests.get(spotsUrl)
data = response.json()
# extract asset list
spots = pd.DataFrame.from_dict(data)
# conversion factor for volume
for index, row in spots.iterrows():
    baseAssetData = assets.loc[assets.index == row['baseID']]
    baseAssetFactor = int(baseAssetData['unitinfo.conventional.conversionFactor'])
    spots.at[index, 'vol24'] = spots.at[index, 'vol24'] / baseAssetFactor
    baseAssetPriceUSDT = float(baseAssetData['ReferenceRateUSD'].values[0])
    spots.at[index, 'vol24USD'] = spots.at[index, 'vol24'] * baseAssetPriceUSDT

# replace base with strings
spots['baseID'] = spots['baseID'].apply(lambda x: assets.loc[x].symbol)
# replace quote with strings
spots['quoteID'] = spots['quoteID'].apply(lambda x: assets.loc[x].symbol)
spots['date'] = pd.to_datetime(spots['stamp'],unit='ms')
print(spots)
# drop stamp column
spots = spots.drop(columns=['stamp'])

# path for saving the data
pathStr = basePathStr + '/spots/' + yearMonthStr
if not os.path.exists(pathStr):
    os.makedirs(pathStr)
filename = pathStr + todayStr + '.csv'
# save to csv
spots.to_csv(filename,index=False)

del data, response
# grab book data
for index, row in markets.iterrows():
    # get market name
    marketName = str(row['name'])
    # get base asset dividing factor
    baseAssetData = assets.loc[assets.symbol==row['base']]
    baseAssetFactor = int(baseAssetData['unitinfo.conventional.conversionFactor'])
    # create url for this market
    booksUrl = "https://dex.decred.org/api/orderbook/" + row.base + '/' + row.quote
    response = requests.get(booksUrl)
    data = response.json()
    # extract asset list
    books = pd.DataFrame.from_dict(data['orders'])
    if not books.empty:
        # drop stamp column
        books = books[['side', 'qty','rate','time']].copy()
        books['time'] = pd.to_datetime(books['time'], unit='ms')
        books['qty'] = books['qty'] / baseAssetFactor
        books = books.sort_values(by='rate', ascending=False)
        # path for saving the data
        pathStr = basePathStr + '/orderbook/' + marketName + '/' + yearMonthStr
        if not os.path.exists(pathStr):
            os.makedirs(pathStr)
        filename = pathStr + todayStr + '.csv'
        # save to csv
        books.to_csv(filename,index=False)
    # add a pause
    time.sleep(1)

