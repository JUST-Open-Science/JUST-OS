# Copyright 2024 Akari Asai
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# This file contains code derived from OpenScholar
# Repository: https://github.com/AkariAsai/OpenScholar

example_passages_rag = """
[0] Title: Attributed Question Answering: Evaluation and Modeling for Attributed Large Language Models Text: Roberts et al. (2020) shows that T5 (Raffel et al., 2020) can perform a new task formulation, closedbook QA. Concretely, T5 can produce answers to questions without access to any corpus at inference time, instead producing answers based on its model parameters, tuned to remember information digested in pretraining.\n
[1] Title: Reliable, Adaptable, and Attributable Language Models with Retrieval Text: Unlike parametric LMs—which use large-scale text data only during training—retrieval-augmented LMs leverage an external large-scale collection of documents (datastore) at inference by selecting relevant documents from the datastore (Asai et al., 2023a). Retrieval-augmented LMs can W1: largely reduce factual errors (Mallen et al., 2023), W2: provide better attributions (Gao et al., 2023a), W3: enabling flexible opt-in and out of sequences (Min et al., 2024).
[2] Title: Atlas: Few-shot Learning with Retrieval Augmented Language Models Text: In this work we present Atlas, a carefully designed and pre-trained retrieval augmented language model able to learn knowledge intensive tasks with very few training examples. We perform evaluations on a wide range of tasks, including MMLU, KILT and NaturalQuestions, and study the impact of the content of the document index, showing that it can easily be updated. Notably, Atlas reaches over 42% accuracy on Natural Questions using only 64 examples, outperforming a 540B parameters model by 3% despite having 50x fewer parameters.
[3] Title: Language Models are Few-Shot Learners Text: Similarly, GPT-3 achieves 64.3% accuracy on TriviaQA in the zero-shot setting, 68.0% in the one-shot setting, and 71.2% in the few-shot setting, the last of which is state-of-the-art relative to fine-tuned models operating in the same closed-book setting.
[4] Title: When Not to Trust Language Models: Investigating Effectiveness of Parametric and Non-Parametric Memories Text:  On both datasets, LMs’ memorization (RQ1) is often limited to the popular factual knowledge and even GPT-3 davinci-003 fails to answer the majority of the long-tail questions. Moreover, on such questions, scaling up models does not significantly improve the performance. This also suggests that we can predict if LMs memorize certain knowledge based on the information presented in the input question only. We next investigate whether a semi-parametric approach that augments LMs with retrieved evidence can mitigate the low performance on questions about less popular entities (RQ2). Nonparametric memories largely improve performance on long-tail distributions across models.
[5] Title: Democratizing Large Language Models via Personalized Parameter-Efficient Fine-tuning Text: Personalization in large language models (LLMs) is increasingly important, aiming to align LLM’s interactions, content, and recommendations with individual user preferences. Recent advances in LLM personalization have spotlighted effective prompt design, by enriching user queries with non-parametric knowledge through behavior history retrieval and textual profiles. However, these approaches were limited due to a lack of model ownership, resulting in constrained customization and privacy issues. Moreover, they often failed to accurately capture user behavior patterns, especially in cases where user data were complex and dynamic. To address these shortcomings, we introduce One PEFT Per User (OPPU), which employs personalized parameter-efficient fine-tuning (PEFT) modules, to store user-specific behavior patterns and preferences.
[6] Title: RECOMP: Improving Retrieval-Augmented LMs with Context Compression and Selective Augmentation Text:  Retrieval-augmented language models (RALMs) (Khandelwal et al., 2019; Izacard et al., 2022; Lewis et al., 2020; Borgeaud et al., 2022) have shown impressive performance on knowledge-intensive tasks (Kwiatkowski et al., 2019; Petroni et al., 2021). Simply prepending retrieved documents to the input without updating the language models (LMs) (Shi et al., 2023b; Ram et al., 2023; Si et al., 2022) allows retrieval augmentation even for black-box LMs, but such approach comes with limitations. First, it increases computational costs as LMs now encode substantially more tokens. Second, even if we manage to adapt LMs to efficiently incorporate longer context (Beltagy et al., 2020; Zaheer et al., 2020), these models struggle to use all information in the context, frequently missing information placed in the middle (Liu et al., 2023). Third, prepending a large number of documents in-context can further confuse LMs with irrelevant information, degrading model performances (Mallen et al., 2022; Shi et al., 2023a).
"""
example_question_rag = (
    "How do language models leverage parametric and non-parametric knowledge?"
)
example_answer_rag = """
Language models leverage both parametric and non-parametric knowledge to perform various tasks.\n
Parametric knowledge refers to the information stored in the model's parameters, which are learned during training [0]. This type of knowledge allows language models to perform tasks such as closed-book question answering, where the model produces answers based on its internal knowledge without accessing any external corpus [0]. However, language models' memorization of parametric knowledge is often limited to popular factual knowledge, and even large models like GPT-3 may fail to answer the majority of long-tail questions [4].\n
On the other hand, non-parametric knowledge is retrieved from an external source, such as a large-scale collection of documents, during inference [1]. This type of knowledge is used in retrieval-augmented language models, which can reduce factual errors, provide better attributions, and enable flexible opt-in and out of sequences [1]. Retrieval-augmented language models have been shown to be effective in few-shot learning scenarios, where they can learn knowledge-intensive tasks with very few training examples [2]. For example, the Atlas model, a retrieval-augmented language model, can reach over 42% accuracy on Natural Questions using only 64 examples, outperforming a 540B parameters model by 3% despite having 50x fewer parameters [2]. Moreover, even without training, simply combining off-the-shelf LMs such as GPT3 with retrieval augmentation can significantly improve performance in long-tail and have been shown to mitigate the low performance on questions about less popular entities[4]. However, retrieval-augmented LMs have several limitations. Specifically, retrieval-augmented LMs can make inference much more inefficient due to increased context length [6].\n
"""
example_answer_rag_incorrect = """
Language models leverage both parametric and non-parametric knowledge to perform various tasks. Parametric knowledge refers to the information stored in the model's parameters, which are learned during training [0]. This type of knowledge allows language models to perform tasks such as closed-book question answering, where the model produces answers based on its internal knowledge without accessing any external corpus [0]. However, language models' memorization of parametric knowledge is often limited to popular factual knowledge, and even large models like GPT-4 often fail to answer the majority of long-tail questions [4].\n
On the other hand, non-parametric knowledge is retrieved from an external source, such as a large-scale collection of documents, during inference [1]. This type of knowledge is used in retrieval-augmented language models, which can reduce factual errors, provide better attributions, and enable flexible opt-in and out of sequences [1]. Retrieval-augmented language models have been shown to be effective in few-shot learning scenarios, where they can learn knowledge-intensive tasks with very few training examples [2]. For example, the Atlas model, a retrieval-augmented language model, can reach over 42% accuracy on Natural Questions using only 64 examples, outperforming a 540B parameters model by 3% despite having 50x fewer parameters [2]. Moreover, even without training, simply combining off-the-shelf LMs such as GPT3 with retrieval augmentation can significantly improve performance in long-tail and have been shown to mitigate the low performance on questions about less popular entities [4]. However, retrieval-augmented LMs have several limitations. Specifically, retrieval-augmented LMs can make inference much more inefficient due to increased context length [6].\n
"""

prompts_w_references = (
    "Provide a detailed, informative answer to the following research-related question. Your answer should be more than one paragraph, offering a comprehensive overview. "
    "Base your answer on multiple pieces of evidence and references, rather than relying on a single reference for a short response. Aim to give a holistic view of the topic. "
    "Ensure the answer is well-structured, coherent and informative so that real-world scientists can gain a clear understanding of the subject. Rather than simply summarizing multiple papers one by one, try to organize your answers based on similarities and differences between papers. "
    "Make sure to add citations to all citation-worthy statements using the provided references (References), by indicating the citation numbers of the corresponding passages. "
    "More specifically, add the citation number at the end of each relevant sentence e.g., 'This work shows the effectiveness of problem X [1].' when the passage [1] in References provides full support for the statement. "
    "You do not need to add the author names, title or publication year as in the ordinal paper writing, and just mention the citation numbers with your generation. "
    "Not all references may be relevant, so only cite those that directly support the statement. "
    "You only need to indicate the reference number, and you do not need to add Reference list by yourself. "
    "If multiple references support a statement, cite them together (e.g., [1][2]). Yet, for each citation-worthy statement, you only need to add at least one citation, so if multiple eviences support the statement, just add the most relevant citation to the sentence. "
    "Your answer should be marked as [Response_Start] and [Response_End].\n"
    "Here's an example:\n##\n"
    "References: \n{example_passages}"
    "\nQuestion: {example_question}"
    "\n[Response_Start]{example_answer}[Response_End]\nNow, please answer this question\n##\n"
)
generation_demonstration_prompts = prompts_w_references.format_map(
    {
        "example_passages": example_passages_rag,
        "example_question": example_question_rag,
        "example_answer": example_answer_rag,
    }
)
generation_instance_prompts_w_references = (
    generation_demonstration_prompts
    + "References:\n {context_items}\nQuestion: {query}\n"
)

system_prompt = (
    "You are a helpful AI assistant for scientific literature review. "
    "Please carefully follow user's instruction and help them to understand the most recent papers."
)
