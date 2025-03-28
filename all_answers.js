const answers = []

const category = document.querySelector(".secondarytitle").innerText.match(/Results for (.+)/)[1]
let counter = 0;
while (true) {
	let next = document.querySelector(".modelname:not([checked])")
	if (next == null)
		break;
	next.setAttribute("checked", "")
	const match = next.textContent.match(/(.+) — (Colored|P\/T)/);
	if (match) {
		const modelType = match[2] == 'Colored' ? 'COL' : "PT";
		const name = match[1]
		next.classList.add(`${name}-${modelType}`)
		item = document.querySelector(`tr:has(td.${name}-${modelType}) ~ tr>td>a.expectedresult`);
		while (item != null) {
			let key = "a" + (counter++).toString()
			item.classList.add(key)
			ok = document.querySelector(`tr>td>.${key}>span>p>b`);
			const fullName = `${name}-${modelType}-${item.innerText}`;
			const filteredAnswers = ok.innerText.replaceAll(" ", "").replaceAll(")", "").replaceAll("(", "");

			for (let i = 0; i < filteredAnswers.length; i++) {
				answers.push({
					name: fullName,
					category: category,
					queryIndex: i,
					answer: filteredAnswers[i]
				});
			}
			item = document.querySelector(`tr:has(td>.${key}) + tr>td>a.expectedresult`);
		}
	}
}

console.log(answers.map((o => [
	o.name, o.category, o.queryIndex, o.answer
].join(','))).join('\n'));