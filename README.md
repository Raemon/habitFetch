habitFetch
============

Python script that fetches your daily and habit history from HabitRPG, and stores it in a database so you can visualize it later.

To use this script, set up a crontab or other automated tool that can run a python script at least once a day.

##Setup##

Edit the settings.py file to include your habitRPG user_id and api_key. (Find these in the API section of the habitRPG website, after logging in)

##Potential Problems##

	Problems with HabitRPG:
		- sometimes an item has no history
		- sometimes an item's id doesn't follow the id format (I once saw an id that was the same as the name)


	Problems with HabitFetch
		- if an item has history, make sure that history is used instead of creating one based off "today"

##License##

The MIT License (MIT)

Copyright (c) 2015 Raymond Arnold, Nathan Hwang

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.


<!-- ## Initializtion ##
```javascript
var habitapi = require('habit-rpg');
new habitapi(userId, apiKey);
```

## User ##
**GET /user**

Gets the full user object
```javascript
.user.getUser(function(response, error){})
``` -->
