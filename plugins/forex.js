const axios = require("axios");

module.exports = {
  name: "forex",
  alias: ["forex", "fx", "price"],
  desc: "Get Forex live prices",
  category: "finance",
  usage: "forex EURUSD",
  react: "💹",

  start: async (client, m, { text, args, prefix, command }) => {
    try {
      let symbol = args[0] ? args[0].toUpperCase() : "EURUSD";
      let base = symbol.slice(0, 3);   // Example: EUR
      let quote = symbol.slice(3, 6);  // Example: USD

      let url = `https://api.exchangerate.host/latest?base=${base}&symbols=${quote}`;
      let { data } = await axios.get(url);

      if (!data || !data.rates || !data.rates[quote]) {
        return m.reply("❌ Invalid symbol. Example: `.forex EURUSD`");
      }

      let price = data.rates[quote];

      let msg = `💹 *Forex Live Price*\n\n🔹 Pair: *${symbol}*\n💰 Price: *${price}*\n\n_Powered by PASIYA-MD_`;

      await client.sendMessage(m.chat, { text: msg }, { quoted: m });

    } catch (err) {
      console.log(err);
      return m.reply("❌ Error fetching forex data.");
    }
  },
};
