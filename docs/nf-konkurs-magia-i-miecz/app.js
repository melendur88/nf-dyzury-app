const meta = document.querySelector("#meta");
const summary = document.querySelector("#summary");
const users = document.querySelector("#users");
const stories = document.querySelector("#stories");

const text = (value) => document.createTextNode(value);

function cell(value) {
  const td = document.createElement("td");
  td.append(text(String(value)));
  return td;
}

function statistic(value, label) {
  const item = document.createElement("div");
  const number = document.createElement("strong");
  number.append(text(String(value)));
  const description = document.createElement("span");
  description.append(text(label));
  item.append(number, description);
  return item;
}

fetch("report.json", { cache: "no-store" })
  .then((response) => {
    if (!response.ok) throw new Error("Brak raportu");
    return response.json();
  })
  .then((report) => {
    const updated = new Date(report.updatedAt).toLocaleString("pl-PL", {
      dateStyle: "medium",
      timeStyle: "short",
      timeZone: "Europe/Warsaw",
    });
    meta.textContent = `Od ${report.since}. Ostatnie odświeżenie: ${updated}.`;
    summary.replaceChildren(
      statistic(report.summary.stories, "opowiadań"),
      statistic(report.summary.authors, "autorów"),
      statistic(report.summary.comments, "komentarzy"),
      statistic(report.summary.substantiveComments, "merytorycznych")
    );
    users.replaceChildren(...report.users.map((user) => {
      const row = document.createElement("tr");
      row.append(
        cell(user.username),
        cell(user.submittedStories),
        cell(user.storiesCommented),
        cell(`${user.comments} / ${user.substantiveComments}`),
        cell(user.ownStoryComments)
      );
      return row;
    }));
    stories.replaceChildren(...report.stories.map((story) => {
      const article = document.createElement("article");
      const heading = document.createElement("h3");
      const link = document.createElement("a");
      link.href = story.url;
      link.textContent = story.title;
      heading.append(link);
      const details = document.createElement("p");
      details.className = "details";
      details.textContent = `${story.author} · ${story.comments} komentarzy (${story.substantiveComments} merytorycznych)`;
      article.append(heading, details);
      if (story.commenters.length) {
        const commenters = document.createElement("p");
        commenters.className = "commenters";
        commenters.textContent = story.commenters.map((commenter) => `${commenter.username}: ${commenter.comments}`).join(" · ");
        article.append(commenters);
      }
      return article;
    }));
  })
  .catch(() => {
    meta.textContent = "Raport nie jest jeszcze dostępny. Spróbuj ponownie za chwilę.";
  });
