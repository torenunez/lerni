# Learning concepts

These concepts guide how Lerni's conversation and interest map are designed ([spec](../plans/specs/04-interest-map.md#learning-concepts-in-the-design)). Examples are illustrative. Where a concept shapes Lerni directly, an **In Lerni** line says how.

**Feynman technique.** Explain an idea in plain language as if teaching a beginner. Notice where the explanation breaks down, check the source, and try again. Keep the explanation simple and accurate. Research on learning by teaching supports related practices, rather than validating one fixed "Feynman" routine. [Related research](https://doi.org/10.1016/j.cedpsych.2013.06.001).

*Example:* Explain why doubling a recipe requires doubling every ingredient. If you cannot explain what happens when only the flour doubles, revisit ratios and revise the explanation.

*In Lerni:* the admin tool's four steps (raw notes, simple explanation, gaps, refined explanation). In the student app, the agent now and then asks the student to explain a goal back in their own words; a goal they explained is drawn solid on their map. Explaining once is not treated as mastery.

**Spaced repetition.** Revisit material across separate sessions to strengthen retention. The useful spacing depends on the material and how long it needs to be remembered; there is no single best schedule. [Research](https://digitalcommons.usf.edu/psy_facpub/1766/).

*Example:* Ask the learner to explain a ratio today, revisit it a few days later, and return to it the following week. Adjust the timing based on what they remember. These intervals are illustrative.

*In Lerni:* the admin tool schedules reviews with SM-2 and asks you to explain from memory before showing your old answer ([details](reference/admin.md#scheduling)). In the student app, map entries fade when they haven't come up lately, and the agent prefers returning to faded goals the student once explained; fuller recall checks come in Release 2.

**Analogical scaffolding and transfer.** Analogical scaffolding uses guided comparisons to make an unfamiliar idea easier to understand. Transfer means applying what was learned to a different problem or context. Make the shared principle explicit, then check whether the learner can use it independently. [Research on scaffolding](https://journals.aps.org/prper/abstract/10.1103/PhysRevSTPER.3.010109) · [Research on transfer](https://gwern.net/doc/psychology/1983-gick.pdf).

*Example:* Compare doubling a recipe with enlarging a scale model: both preserve ratios. Then ask the learner to work out a paint mixture without that prompt.

*In Lerni:* once a goal has a bridge from one interest, the agent's next bridge to it comes from a different interest (fractions through cars, later through pizza), without pointing out the link. Two bridges into one goal are a chance to check transfer, not proof of it.

**Anchored instruction.** Organize learning around a meaningful problem or story. The problem gives the learner a reason to investigate and apply several concepts throughout the activity. [Research](https://journals.sagepub.com/doi/abs/10.3102/0013189X019006002).

*Example:* Design a garden within a given space and budget. Use a map, prices, and plant requirements to explore area, measurement, and costs.

**Culturally responsive teaching.** Build on the learner's languages, cultural knowledge, and lived experience. This shapes examples, communication, and participation while maintaining strong learning goals. Learn about the individual; avoid assumptions based on their background. [Research](https://journals.sagepub.com/doi/10.1177/0022487102053002003).

*Example:* Ask the learner to explain a family cooking practice, including home-language terms. Use it to explore measurement and compare methods.

*In Lerni:* every conversation starts from the student's own interests, named in their own words on the map.

**Conceptual bridging.** Connect existing understanding to a new concept through intermediate ideas or examples. A specific research approach, *bridging analogies*, uses a sequence of comparisons to make the connection understandable. [Research](https://onlinelibrary.wiley.com/doi/abs/10.1002/tea.3660301007).

*Example:* Explore how a compressed spring pushes back, then how a flexible board supports weight, then why a sturdy table pushes upward on a book.

*In Lerni:* a bridge is the agent leading from an interest to a goal in conversation. Stepping-stone ideas in between are not recorded, to keep the map minimal.

**Zone of proximal development (ZPD).** The range between what a learner can do independently and what they can do with capable guidance. Identify it through the learner's performance on particular tasks. [Research](https://docdrop.org/static/drop-pdf/Vygotksy1978_ZPD-8W6rm.pdf).

*Example:* A learner adds fractions with matching denominators alone and adds fractions with different denominators using fraction strips and prompts. The supported task may fall within their ZPD.

*In Lerni:* if the student changes the subject right after a bridge, the agent backs off that goal for a few days and then tries a gentler way in. That is a hint about readiness, not a stored score.

**Scaffold distance.** No standard educational definition or validated measure was found under this name. For Lerni, we could define it as the number of planned teaching transitions from a starting concept to a target. This would be a planning convention, not a measure of difficulty or ZPD.

*Example:* Toy-car motion → distance over time → speed → changing speed contains three transitions. Their difficulty depends on the learner and the support provided.

*In Lerni:* not used; stepping stones between an interest and a goal aren't recorded.

**Conceptual hierarchies.** Organize concepts from broad categories to more specific ones. Concepts can also connect across branches. A hierarchy describes how knowledge is organized; teaching order is a separate decision. [Research](https://users.cs.northwestern.edu/~paritosh/papers/sketch-to-models/Novak-Canas-TheoryUnderlyingConceptMapsHQ.pdf).

*Example:* Living things → plants → flowering plants → roses. An activity might start with a familiar rose and work toward the broader categories.

*In Lerni:* not used; the map stays flat (interests, goals, and links) to keep it minimal.

## For Lerni

Keep what the map shows (what came up, for how long, what was explained once) separate from evidence of capability. Use these ideas to guide the agent and the educator's judgment, and watch real conversations. Time spent, a bridge, or one explanation does not prove mastery.
