
const fs = require('fs');
const path = require('path');
const config = require('../settings');
const { ven } = require('../pasiya');

ven({
  on: "body"
},    
async (robin, mek, m, { from, body, isOwner }) => {
    const filePath = path.join(__dirname, '../my_data/autovoice.json');
    const data = JSON.parse(fs.readFileSync(filePath, 'utf8'));
    for (const text in data) {
        if (body.toLowerCase() === text.toLowerCase()) {
            
            if (config.AUTO_VOICE === 'true') {
                //if (isOwner) return;        
                await robin.sendPresenceUpdate('recording', from);
                await robin.sendMessage(from, { audio: { url: data[text] }, mimetype: 'audio/mpeg', ptt: true }, { quoted: mek });
            }
        }
    }                
});

//auto sticker 
ven({
  on: "body"
},    
async (robin, mek, m, { from, body, isOwner }) => {
    const filePath = path.join(__dirname, '../my_data/autosticker.json');
    const data = JSON.parse(fs.readFileSync(filePath, 'utf8'));
    for (const text in data) {
        if (body.toLowerCase() === text.toLowerCase()) {
            
            if (config.AUTO_STICKER === 'true') {
                //if (isOwner) return;        
                await robin.sendMessage(from,{sticker: { url : data[text]},package: 'S_I_H_I_L_E_L'},{ quoted: mek })   
            
            }
        }
    }                
});

//auto reply 
ven({
  on: "body"
},    
async (robin, mek, m, { from, body, isOwner }) => {
    const filePath = path.join(__dirname, '../my_data/autoreply.json');
    const data = JSON.parse(fs.readFileSync(filePath, 'utf8'));
    for (const text in data) {
        if (body.toLowerCase() === text.toLowerCase()) {
            
            if (config.AUTO_REPLY === 'true') {
                //if (isOwner) return;        
                await m.reply(data[text])
            
            }
        }
    }                
});                  
