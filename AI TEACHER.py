import os
import streamlit as st
from PyPDF2 import PdfReader
from googletrans import Translator, LANGUAGES
import openai
from dotenv import load_dotenv
import random
import time
from googleapiclient.discovery import build  # Add this import

load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")
youtube_api_key = os.getenv("YT_API_KEY")

st.set_page_config(page_title="Study Guide Website", page_icon="📚", layout="wide" )
def extract_text_from_pdf(pdf_file):
    try:
        text = ""
        with pdf_file:
            pdf_reader = PdfReader(pdf_file)
            for page_num in range(len(pdf_reader.pages)):
                page = pdf_reader.pages[page_num]
                text += page.extract_text()
        return text
    except Exception as e:
        st.error("Failed to fetch from pdf: " + str(e))
        return None

# def handle_translator(text):        كود ما منه اي فايده
#     translator = Translator()
#     try:
#         translation = translator.translate(text, dest='ar')
#         return translation.text
#
#     except Exception as e:
#         st.error(f"Failed to translate text: {str(e)}")
#         return None

def get_response(text):
        prompt = f'''
                You are an expert in finding keywords that summarizes and captures the essence of text. You will be given text delimited by four backquotes
                Make sure to capture the main points, key arguments, and any supporting evidence presented in the article and summarize this information into a possible phrase that a student might look up on Youtube.
                Your phrase should be informative and well-structured, ideally consisting of 1 sentence each.
                text: {text}'''

        response = openai.ChatCompletion.create(  # response that I'll get from chatgpt
            model="gpt-3.5-turbo",  # version / model of chatgpt we'll use (free version)
            messages=[  # messages we'll send to chatgpt - which is a list
                {
                    "role": "system",
                    "content": prompt,  # my prompt
                },
            ],
        )
        return response["choices"][0]["message"]["content"]


# Function to search for YouTube videos based on keywords
def search_youtube_videos(query):
    youtube = build("youtube", "v3", developerKey=youtube_api_key)
    request = youtube.search().list(
        q=query,
        part="snippet",
        type="video",
        maxResults=3  # number of results
    )
    response = request.execute()
    video_ids = [item["id"]["videoId"] for item in response["items"]]
    video_links = [f"https://www.youtube.com/watch?v={video_id}" for video_id in video_ids]
    return video_links


def process_text_with_gpt(text, task_type):
    # Prepare the system and user messages for chat
    messages = [
        {"role": "system", "content": "You are an AI trained to assist users."},
    ]
    if task_type == 'Summarize':
        user_message = f'''you are an expert in summarizing lectures to students and help them understand, summarize the given chapter in a clear and understood way.
         it should be informative,well structured, with headers a bit bulked ,beneficial. make sure to include all the information in the text, make it detailed,
         always add emojis in the headers to make it clear,
         in the end give one clear numberd list of all the mentioned formulas, please help the students understand the lecture through this summary,
         not need to mention the problems or hw {text}'''

    elif task_type == 'Chat with a Professional':
        user_message = f"you are an expert teacher at all subjects, explain the topic in a very clear and easy way to a 8yo student ( dont mention their age) and ask if they need more help : {text}"

    elif task_type == 'ملخص بالعربي':
        user_message = f'''. اسمع انت معلم تدرس كل المواد وتدرس الصف الابتدائي,  اشرح الدرس هذا بطريقة سهله وتكلم باللهجة العامية .لا تقول ( فلا تتردد في طلب المساعده) فقط انهي انهي النقاش ب(اتمنى اني قدرت افهمك)ولا تجاوب على سؤال من برا الدرس ابداً.{text}'''

    # elif task_type == "YouTube Video Suggestion":
    #     user_message = f"Generate YouTube search keywords based on the following text: {text}"

    else:
        user_message = "Process this text: " + text

    messages.append({"role": "user", "content": user_message})

    try:

        myresponse = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=messages,
            max_tokens=500
        )
        return myresponse['choices'][0]['message']['content']

    except Exception as e:
        return f"Failed to fetch response from OpenAI: {str(e)}"

def generate_quiz(text, num_questions):  # Define a function to generate quiz questions from the text
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are an AI trained to create educational multiple-choice quizzes."},
                {"role": "user",
                 "content": f"Generate {num_questions} multiple-choice questions with four choices each based on the following text: {text}"}
            ],
            max_tokens=1500
        )  # Request generation of multiple-choice questions from the OpenAI model
        quiz_questions = []  # Initialize a list for the quiz questions
        quiz_content = response['choices'][0]['message']['content'].split(
            '\n\n')  # Split the retrieved text into separate blocks
        for block in quiz_content:  # Loop through each text block
            lines = block.strip().split('\n')  # Split the block into separate lines
            if len(lines) > 1:
                question = lines[0]  # The first line is the question
                options = lines[1:]  # The following lines are the options
                if len(options) >= 4:  # Ensure there are at least 4 options
                    options = options[:4]  # Only take the first 4 options
                else:
                    continue  # Skip this question if there are less than 4 options

                # Randomly choose a position for the correct answer
                correct_index = random.randint(0, 3)  # Get a random index between 0 and 3
                ordered_options = options  # Use the original options order
                quiz_questions.append({
                    'question': question,
                    'options': ordered_options,
                    'correct_index': correct_index
                })  # Add the question, options, and correct index to the list
        return quiz_questions  # Return the list of quiz questions
    except Exception as e:
        st.error(f"Failed to generate quiz: {str(e)}")  # Display an error message if generation fails
        return None  # Return None if generation fails


def get_feedback_for_answers(quiz_questions, user_answers):  # Define a function to get feedback for answers
    feedback = []  # Initialize a list for feedback
    for user_answer, question in zip(user_answers, quiz_questions):  # Loop through user answers and questions
        correct_answer = question['options'][question['correct_index']]  # Get the correct answer
        explanation_response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are an AI trained to provide detailed feedback on quiz answers."},
                {"role": "user",
                 "content": f"Question: {question['question']}\nUser Answer: {user_answer}\nCorrect Answer: {correct_answer}\nExplain why the correct answer is correct and the user answer is correct or not."}
            ],
            max_tokens=500
        )  # Request an explanation for the correct answer from the OpenAI model
        explanation = explanation_response['choices'][0]['message']['content']  # Get the explanation
        feedback.append((correct_answer, explanation))  # Add the correct answer and explanation to the feedback list
    return feedback  # Return the feedback list


def handle_quiz(quiz_questions):  # Define a function to handle displaying questions and collecting user answers
    user_answers = []  # Initialize a list for user answers
    if quiz_questions:
        with st.form("quiz_form"):  # Create a form for collecting answers
            for index, question in enumerate(quiz_questions):  # Loop through the questions
                st.write(f"**Question {index + 1}:** {question['question']}")  # Display the question
                options = question['options']  # Get the options
                chosen_option = st.radio(f"Choose one option:", options,
                                         key=f"option_{index}")  # Display the options as radio buttons
                user_answers.append(chosen_option)  # Add the user's choice to the list of answers
            submitted = st.form_submit_button("Submit All Answers")  # Create a submit button for the form
            if submitted:
                st.session_state.quiz_submitted = True  # Mark the quiz as submitted
                feedback = get_feedback_for_answers(quiz_questions, user_answers)  # Get feedback for the answers

                correct_answers = sum(
                    user_answer == question['options'][question['correct_index']]
                    for user_answer, question in zip(user_answers, quiz_questions)
                )  # Calculate the number of correct answers
                st.markdown(
                    f"### Quiz completed! You scored {correct_answers} out of {len(quiz_questions)}.")  # Display the final score

                for idx, (correct_answer, feedback_message) in enumerate(
                        feedback):  # Display feedback for each question
                    st.markdown(f"**Feedback for Question {idx + 1}:**")
                    st.markdown(f"- **Correct Answer:** {correct_answer}")
                    st.markdown(f"- **Explanation:** {feedback_message}")


def display_timer(duration):
    timer_placeholder = st.empty()
    end_time = time.time() + duration * 60
    while time.time() < end_time:
        if st.session_state.get("quiz_submitted", False):  # Stop the timer if the quiz is submitted
            break
        remaining_time = int(end_time - time.time())
        minutes, seconds = divmod(remaining_time, 60)
        timer_placeholder.markdown(f"Time Remaining: {minutes:02}:{seconds:02}")
        time.sleep(1)
    if not st.session_state.get("quiz_submitted", False):  # Only display "Time's up" if the quiz was not submitted
        timer_placeholder.markdown("### Time's up!")
        st.error("Time's up!")


def quizlet(text):  # Define the main function to display the user interface
    st.header("Quiz Generator")  # Page header
    if text:
            num_questions = st.number_input("Enter the number of questions:", min_value=1, max_value=20,
                                            step=1)  # Input for the number of questions
            time_minutes = st.number_input("Enter the quiz duration in minutes:", min_value=1, max_value=120,
                                           step=1)  # Input for the quiz duration

            if st.button("Generate Quiz"):  # Button to generate the quiz
                quiz_questions = generate_quiz(text, num_questions)  # Generate quiz questions
                if quiz_questions:
                    st.session_state.quiz_questions = quiz_questions  # Save quiz questions in session state
                    st.session_state.time_minutes = time_minutes  # Save quiz duration in session state

    if "quiz_questions" in st.session_state and "time_minutes" in st.session_state:
        quiz_questions = st.session_state.quiz_questions
        time_minutes = st.session_state.time_minutes

        st.write("Refresh the page if you want to take another quiz :D")
        st.write("The timer is at the bottom of the page!")

        # Display quiz questions
        handle_quiz(quiz_questions)  # Handle displaying questions and collecting answers

        # Display timer
        display_timer(time_minutes)


def main():
    st.title("📚 Study Guide Website")
    st.markdown("Welcome to the Study Guide Website! This platform allows you to interact with your lecture slides and make studying easier.")

    uploaded_file = st.file_uploader("Please upload a PDF file", type=["pdf"])
    if uploaded_file:
        text = extract_text_from_pdf(uploaded_file)
        if text:
            option = st.selectbox("Choose what you want to do with your PDF file:",
                                  ["Summarize", "ملخص بالعربي", "YouTube Video Suggestion", "Chat with a Professional", "Test your Understanding"])

            if option == "Chat with a Professional":
                response = process_text_with_gpt(text, option)
                st.subheader("Explanation of the Lesson")
                st.text_area("Explanation:", value=response, height=300)
                user_input = st.text_input("Your question:")
                if st.button("Ask"):
                    if user_input:
                        response = openai.Completion.create(
                            engine="gpt-3.5-turbo-instruct",
                            prompt=f"Context: {text}\nQuestion: {user_input}\nAnswer:",
                            max_tokens=200
                        )
                        answer = response['choices'][0]['text'].strip()

                        st.header("Chatbot Response:")
                        st.write(answer)
                    else:
                        st.error("Please enter a question to ask the chatbot.")


            if option == "YouTube Video Suggestion":
                response1 = get_response(text)
                # look up Youtube videos related to the phrase
                phrase = {response1};
                videos = search_youtube_videos(phrase)
                st.subheader(f"Related videos:")
                for video in videos:
                    st.markdown(video)



            if option == "Test your Understanding":
                quizlet(text)

            if option == "Summarize" or option == "ملخص بالعربي":
                result = process_text_with_gpt(text, option)
                st.write(result)



        else:
            st.error("No text could be extracted from the uploaded PDF.")
    else:
        st.warning("Please upload a PDF to enable functionality options.")


if __name__ == "__main__":
    main()
